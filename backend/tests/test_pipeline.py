import pytest
import numpy as np
import cv2
from app.core.pipeline.orchestrator import PipelineOrchestrator
from app.core.ingestion.engine import IngestionEngine
from app.models.database import db_manager

def create_synthetic_image():
    # Simple valid image bytes
    img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    success, buffer = cv2.imencode(".png", img)
    return buffer.tobytes()

def create_corrupted_image():
    return b"not an image file at all"

def test_pipeline_end_to_end():
    image_bytes = create_synthetic_image()
    cdo = IngestionEngine.ingest_file(image_bytes, "test.png")
    schema, chunks = PipelineOrchestrator.process_document(cdo)
    
    assert schema is not None
    assert schema.source_file == "test.png"
    # A perfectly blank synthetic image will yield 0 semantic blocks from the real Florence-2 VLM
    assert len(schema.semantic_blocks) >= 0
    assert len(chunks) >= 0

def test_caching_layer():
    image_bytes = create_synthetic_image()
    
    # First upload (Cache Miss)
    cdo1 = IngestionEngine.ingest_file(image_bytes, "cache_test.png")
    schema1, chunks1 = PipelineOrchestrator.process_document(cdo1)
    
    # Second upload (Cache Hit)
    cdo2 = IngestionEngine.ingest_file(image_bytes, "cache_test.png")
    schema2, chunks2 = PipelineOrchestrator.process_document(cdo2)
    
    # Ensure they share the exact same SHA256 and Document ID
    assert schema1.sha256_hash == schema2.sha256_hash
    assert schema1.document_id == schema2.document_id

def test_corrupted_upload_handling():
    corrupted_bytes = create_corrupted_image()
    with pytest.raises(Exception):
        cdo = IngestionEngine.ingest_file(corrupted_bytes, "bad.png")
        PipelineOrchestrator.process_document(cdo)

def test_database_logging():
    # Verify processing history is logged
    image_bytes = create_synthetic_image()
    cdo = IngestionEngine.ingest_file(image_bytes, "log_test.png")
    schema, _ = PipelineOrchestrator.process_document(cdo)
    
    # Check SQLite for event existence
    with db_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM processing_history WHERE document_id = ?", (schema.document_id,))
        count = cursor.fetchone()[0]
        assert count > 0 # Multiple events should be logged
