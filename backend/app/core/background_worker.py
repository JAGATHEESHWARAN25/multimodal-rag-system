import asyncio
import logging
from typing import Dict, Any, Optional
from app.models.database import db_manager
from app.config import UPLOADS_DIR
from app.core.ingestion.engine import IngestionEngine
from app.core.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

class HardenedBackgroundWorker:
    """Hardened, resilient SQLite-backed background worker with retries, backoff, concurrency limits, and stale-job recovery."""

    def __init__(self, max_concurrent_jobs: int = 2, max_retries: int = 3):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.max_retries = max_retries
        self.retry_counts: Dict[str, int] = {}
        self._scheduled_job_ids = set()

    async def start(self):
        if not self.is_running:
            self.is_running = True
            # Sweep stale jobs stuck in PROCESSING from previous crashes
            recovered = db_manager.recover_stale_jobs(stale_seconds=300)
            if recovered > 0:
                logger.info(f"Background Worker recovered {recovered} stale jobs on startup.")
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("Hardened Background Worker started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Hardened Background Worker stopped.")

    async def _worker_loop(self):
        while self.is_running:
            try:
                jobs = db_manager.get_queued_jobs()
                for job in jobs:
                    if not self.is_running:
                        break
                    job_id = job["id"]
                    if job_id in self._scheduled_job_ids:
                        continue
                    self._scheduled_job_ids.add(job_id)
                    # Process concurrently up to semaphore limit
                    asyncio.create_task(self._guarded_process_job(job))
            except Exception as e:
                logger.error(f"Error in background worker loop: {e}")
            await asyncio.sleep(2)

    async def _guarded_process_job(self, job: Dict[str, Any]):
        job_id = job["id"]
        document_id = job.get("document_id")
        try:
            async with self.semaphore:
                await asyncio.to_thread(self._sync_process_job, job)
        except Exception as e:
            current_retries = self.retry_counts.get(job_id, 0) + 1
            self.retry_counts[job_id] = current_retries

            if current_retries <= self.max_retries:
                backoff_delay = 2 ** current_retries
                logger.warning(f"Job {job_id} failed (attempt {current_retries}/{self.max_retries}): {e}. Retrying in {backoff_delay}s...")
                await asyncio.sleep(backoff_delay)
                db_manager.update_job_status(job_id, "QUEUED", error=f"Retry {current_retries}: {str(e)}")
            else:
                logger.error(f"Worker crashed during job {job_id}: {str(e)}")
                db_manager.update_job_status(job_id, "FAILED", error=str(e))
                if document_id:
                    db_manager.update_document_status(document_id, "FAILED")
        finally:
            self._scheduled_job_ids.discard(job_id)

    def _is_cancelled(self, job_id: str, document_id: str) -> bool:
        if not self.is_running:
            return True
        doc = db_manager.get_image(document_id)
        if doc and doc.get("status") == "CANCELLED":
            return True
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM background_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row and row[0] == "CANCELLED":
                return True
        return False

    def _sync_process_job(self, job: Dict[str, Any]):
        job_id = job["id"]
        document_id = job["document_id"]
        
        # Check for user cancellation
        if self._is_cancelled(job_id, document_id):
            logger.info(f"Job {job_id} was cancelled.")
            return

        db_manager.update_job_status(job_id, "PROCESSING")
        db_manager.update_document_status(document_id, "PROCESSING")

        doc = db_manager.get_image(document_id)
        if not doc:
            db_manager.update_job_status(job_id, "FAILED", error="Document not found")
            return

        filename = doc["filename"]
        storage_path = UPLOADS_DIR / f"{document_id}_{filename}"

        if not storage_path.exists():
            db_manager.update_job_status(job_id, "FAILED", error="File missing from storage")
            db_manager.update_document_status(document_id, "FAILED")
            return

        with open(storage_path, "rb") as f:
            file_bytes = f.read()

        if self._is_cancelled(job_id, document_id):
            logger.info(f"Job {job_id} was cancelled.")
            return

        ingestion_result = IngestionEngine.ingest_file(file_bytes, filename)

        import types
        from app.core.summarization import DocumentSummarizer
        
        if isinstance(ingestion_result, types.GeneratorType):
            for cdo in ingestion_result:
                if self._is_cancelled(job_id, document_id):
                    logger.info(f"Job {job_id} cancelled during batch ingestion.")
                    return
                cdo.document_id = document_id
                schema, chunks = PipelineOrchestrator.process_document(cdo)
                
                # Generate and inject Global Summary chunk
                global_summary = DocumentSummarizer.summarize_document(document_id)
                chunks.append({
                    "chunk_id": f"summary_{document_id}_{cdo.filename}",
                    "document_id": document_id,
                    "text": f"[GLOBAL SUMMARY]\n{global_summary}",
                    "metadata": {
                        "block_type": "GLOBAL_SUMMARY",
                        "source_file": cdo.filename,
                        "classification": doc.get("classification", "PUBLIC")
                    }
                })
                
                self._index_schema_chunks(chunks)
        else:
            if self._is_cancelled(job_id, document_id):
                logger.info(f"Job {job_id} cancelled before processing.")
                return
            ingestion_result.document_id = document_id
            schema, chunks = PipelineOrchestrator.process_document(ingestion_result)
            
            # Generate and inject Global Summary chunk
            global_summary = DocumentSummarizer.summarize_document(document_id)
            chunks.append({
                "chunk_id": f"summary_{document_id}_{filename}",
                "document_id": document_id,
                "text": f"[GLOBAL SUMMARY]\n{global_summary}",
                "metadata": {
                    "block_type": "GLOBAL_SUMMARY",
                    "source_file": filename,
                    "classification": doc.get("classification", "PUBLIC")
                }
            })
            
            self._index_schema_chunks(chunks)

        if self._is_cancelled(job_id, document_id):
            logger.info(f"Job {job_id} cancelled before final completion.")
            return

        db_manager.update_job_status(job_id, "COMPLETED", progress=100.0)
        db_manager.update_document_status(document_id, "Completed")
        self.retry_counts.pop(job_id, None)
        logger.info(f"Background Job {job_id} for Document {document_id} completed.")

    def _index_schema_chunks(self, chunks: list):
        if not chunks:
            return
            
        try:
            from app.core.vectordb import VectorDatabaseManager
            from app.core.embeddings import LocalEmbeddingsCalculator
            
            # Extract plain text from each chunk dict for the embedding model
            texts = [chunk["text"] for chunk in chunks if "text" in chunk]
            if not texts:
                return
                
            embeddings = LocalEmbeddingsCalculator.calculate_embeddings(texts)
            VectorDatabaseManager.index_document_chunks("document_chunks", chunks, embeddings)
            logger.info(f"Successfully indexed {len(chunks)} chunks into vector database.")
        except Exception as e:
            logger.error(f"Failed to index chunks into vector database: {str(e)}")

worker = HardenedBackgroundWorker()
BackgroundWorker = HardenedBackgroundWorker
