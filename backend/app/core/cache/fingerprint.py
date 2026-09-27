import os
import hashlib
import json
import logging
from typing import Optional, Tuple
from app.models.database import db_manager
from app.models.schema import UniversalKnowledgeSchema
from app.core.events import event_bus

logger = logging.getLogger(__name__)

class DocumentFingerprinter:
    """
    Handles SHA-256 fingerprinting and Level 1 (Exact Duplicate) detection.
    Prevents redundant AI processing for already-ingested files.
    """
    
    @staticmethod
    def generate_hash(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def check_duplicate(sha256_hash: str) -> Tuple[bool, Optional[UniversalKnowledgeSchema]]:
        """
        Queries the database for an exact duplicate hash.
        If found, parses and returns the cached Universal Knowledge Schema.
        """
        row = db_manager.get_document_by_hash(sha256_hash)
        
        if row and row['schema_json']:
            logger.info(f"CACHE HIT: Exact duplicate found for {sha256_hash}")
            db_manager.increment_metric("cache_hits")
            
            try:
                schema_dict = json.loads(row['schema_json'])
                blocks = schema_dict.get('semantic_blocks', [])
                has_content = any(b.get("block_type") in ("paragraph", "heading", "table", "cell", "table_cell", "text", "audio_segment", "video_segment", "diagram", "diagram_node", "poster", "chart") for b in blocks)
                if not blocks or not has_content:
                    logger.info(f"CACHE BYPASS: Cached schema for {sha256_hash} has no substantive content blocks.")
                    return False, None
                schema = UniversalKnowledgeSchema(**schema_dict)
                event_bus.emit("CacheHit", {"sha256": sha256_hash, "document_id": schema.document_id})
                return True, schema
            except Exception as e:
                logger.error(f"Failed to parse cached schema for {sha256_hash}: {e}")
                return False, None
                
        db_manager.increment_metric("cache_misses")
        return False, None
        
    @staticmethod
    def cache_schema(schema: UniversalKnowledgeSchema):
        """Saves the completed schema into the database to enable future cache hits."""
        ext = os.path.splitext(schema.source_file or "")[1].lower().lstrip(".")
        if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            modality = "image"
        elif ext in ["wav", "mp3", "ogg", "m4a", "flac"]:
            modality = "audio"
        elif ext in ["pdf", "docx", "pptx", "csv", "xlsx", "txt"]:
            modality = ext
        else:
            modality = "unknown"

        if modality == "image":
            mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
        elif modality == "audio":
            mime_type = f"audio/{'mpeg' if ext == 'mp3' else ext}"
        elif ext == "pdf":
            mime_type = "application/pdf"
        else:
            mime_type = f"application/{ext}"

        doc_data = {
            "id": schema.document_id,
            "sha256_hash": schema.sha256_hash,
            "filename": schema.source_file,
            "mime_type": mime_type,
            "modality": modality,
            "processing_profile": schema.processing_metadata.profile_used,
            "status": "Completed",
            "schema_json": schema.model_dump_json()
        }
        db_manager.save_document(doc_data)
        logger.info(f"CACHED schema for {schema.sha256_hash}")
        
    @staticmethod
    def generate_vision_cache_key(image_bytes: bytes, engine: str, task: str) -> str:
        h = hashlib.sha256(image_bytes).hexdigest()
        return f"{h}_{engine}_{task}"
        
    @staticmethod
    def check_vision_cache(cache_key: str):
        row = db_manager.get_vision_cache(cache_key)
        if row and row['result_json']:
            db_manager.increment_metric("vision_cache_hits")
            return json.loads(row['result_json'])
        db_manager.increment_metric("vision_cache_misses")
        return None
        
    @staticmethod
    def cache_vision_result(cache_key: str, document_id: str, engine: str, task: str, result_dict: dict):
        db_manager.save_vision_cache(cache_key, document_id, engine, task, json.dumps(result_dict))
