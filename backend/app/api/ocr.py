import logging
import sqlite3
import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from app.config import PROCESSED_DIR, OCR_OUTPUT_DIR
from app.models.database import DatabaseManager
from app.core.image_proc import preprocess_image_pipeline
from app.core.ocr import process_ocr_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["Image Preprocessing & OCR"])

def run_ocr_background_task(image_id: str):
    """Background worker executing image binarization and Tesseract OCR.
    
    Modifies database row status state (Processing -> Completed or Failed).
    """
    logger.info(f"Background OCR task started for document: {image_id}")
    
    # Establish local connection for background worker thread
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Retrieve path details
        record = DatabaseManager.get_image(image_id)
        if not record:
            raise FileNotFoundError(f"Image registry index missing: {image_id}")
            
        original_path = Path(record["storage_path"])
        processed_path = PROCESSED_DIR / f"{image_id}_processed.png"
        
        # Step A: Execute OpenCV Preprocessing (Grayscale, CLAHE, Deskew, Threshold)
        logger.info(f"Binarizing document scan {image_id}...")
        preprocess_image_pipeline(original_path, save_verification_path=processed_path)
        
        # Step B: Run Tesseract subprocess parsing to yield JSON, TXT, and Overlay
        logger.info(f"Extracting characters for document {image_id}...")
        process_ocr_pipeline(
            preprocessed_image_path=processed_path,
            original_image_path=original_path,
            doc_id=image_id
        )
        
        # Step C: Load chunks cache, calculate embeddings, and index in ChromaDB fallback
        logger.info(f"Indexing text chunks in local vector database for {image_id}...")
        chunks_path = OCR_OUTPUT_DIR / f"{image_id}_chunks.json"
        if chunks_path.exists():
            import json
            with open(chunks_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
            
            if chunks:
                from app.core.embeddings import LocalEmbeddingsCalculator
                from app.core.vectordb import VectorDatabaseManager
                
                texts = [chunk["text"] for chunk in chunks]
                embeddings = LocalEmbeddingsCalculator.calculate_embeddings(texts)
                VectorDatabaseManager.index_document_chunks("document_chunks", chunks, embeddings)
                logger.info(f"Successfully indexed {len(chunks)} chunks in vector index.")

        # Commit success status
        cursor.execute("UPDATE images SET status = 'Completed' WHERE id = ?", (image_id,))
        conn.commit()
        logger.info(f"Background OCR and vector indexing task completed successfully for: {image_id}")
    except Exception as e:
        logger.error(f"Background OCR task failed for {image_id}. Error: {str(e)}")
        # Commit failure status
        try:
            cursor.execute("UPDATE images SET status = 'Failed' WHERE id = ?", (image_id,))
            conn.commit()
        except sqlite3.Error as db_err:
            logger.error(f"Failed to record OCR failure to database: {str(db_err)}")
    finally:
        conn.close()

@router.post("/{image_id}/ocr", status_code=status.HTTP_202_ACCEPTED)
def trigger_ocr(image_id: str, background_tasks: BackgroundTasks):
    """Triggers the asynchronous OCR pipeline for a registered image."""
    record = DatabaseManager.get_image(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image record not found in database registry."
        )
        
    # Prevent concurrent duplicate requests if already active
    if record["status"] in ("Processing", "Completed"):
        return {
            "id": image_id,
            "status": record["status"],
            "message": f"OCR is already in '{record['status']}' state. Skipping trigger."
        }
        
    # Set status to 'Processing' immediately in request thread
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE images SET status = 'Processing' WHERE id = ?", (image_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to set status to 'Processing' for {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database write query failed."
        )
        
    # Queue background processing task
    background_tasks.add_task(run_ocr_background_task, image_id)
    
    return {
        "id": image_id,
        "status": "Processing"
    }

@router.get("/{image_id}/ocr/text")
def get_ocr_text(image_id: str):
    """Fetches plain text output from the OCR cache."""
    txt_path = OCR_OUTPUT_DIR / f"{image_id}.txt"
    if not txt_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OCR text cache missing. Please trigger OCR process first."
        )
        
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "id": image_id,
            "text": content
        }
    except IOError as e:
        logger.error(f"Failed to read OCR text cache for {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file from server disk."
        )

@router.get("/{image_id}/ocr/data")
def get_ocr_data(image_id: str):
    """Fetches detailed word coordinate layout objects from the OCR cache."""
    json_path = OCR_OUTPUT_DIR / f"{image_id}.json"
    if not json_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OCR metadata JSON cache missing. Please trigger OCR process first."
        )
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load OCR JSON cache for {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read metadata file from server disk."
        )

@router.get("/{image_id}/ocr/overlay")
def get_ocr_overlay(image_id: str):
    """Serves the generated colored overlay visual png file."""
    overlay_path = OCR_OUTPUT_DIR / f"{image_id}_overlay.png"
    if not overlay_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OCR layout overlay image missing. Please trigger OCR process first."
        )
        
    return FileResponse(str(overlay_path), media_type="image/png")

@router.get("/{image_id}/ocr/chunks")
def get_ocr_chunks(image_id: str):
    """Fetches clean partitioned text chunks from cache (or splits on the fly if needed)."""
    chunks_path = OCR_OUTPUT_DIR / f"{image_id}_chunks.json"
    
    # 1. Try reading the chunks JSON cache directly
    if chunks_path.exists():
        try:
            import json
            with open(chunks_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read chunks JSON cache for {image_id}: {str(e)}")
            
    # 2. If JSON cache is missing but document is Completed (text cache exists), generate on the fly
    record = DatabaseManager.get_image(image_id)
    if not record or record["status"] != "Completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document OCR is not in 'Completed' state. Please analyze the image first."
        )
        
    txt_path = OCR_OUTPUT_DIR / f"{image_id}.txt"
    if not txt_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document text cache is missing."
        )
        
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text_content = f.read()
            
        # Re-run chunking
        from app.core.chunking import package_document_chunks
        chunks = package_document_chunks(
            text=text_content,
            doc_id=image_id,
            source_file=record["filename"],
            dcs=record.get("dcs", 0.0)
        )
        
        # Save to cache
        import json
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=4, ensure_ascii=False)
            
        return chunks
    except Exception as e:
        logger.error(f"Failed to generate chunks on the fly for {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to slice document chunks."
        )
