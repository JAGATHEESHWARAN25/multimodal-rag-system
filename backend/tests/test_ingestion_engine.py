import pytest
import os
import uuid
import numpy as np
import cv2
from app.core.ingestion.detector import FileDetector, FileValidationError, UnsupportedFormatError, FileSizeError
from app.core.ingestion.adapters.manager import AdapterManager
from app.core.ingestion.adapters.image_adapter import ImageAdapter
from app.core.ingestion.engine import IngestionEngine
from app.models.schema import CommonDocumentObject
from app.core.resource_manager import resource_manager

def create_synthetic_image():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    success, buffer = cv2.imencode(".png", img)
    return buffer.tobytes()

def test_file_detector_empty():
    with pytest.raises(FileValidationError):
        FileDetector.analyze_file(b"", "empty.png")

def test_file_detector_unsupported():
    with pytest.raises(UnsupportedFormatError):
        # Fallback will guess extension if random binary data is provided
        FileDetector.analyze_file(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08", "unsupported.xyz")

def test_file_detector_spoofed_extension():
    # Provide text content but name it as PNG
    fake_png_bytes = b"This is just a text file, not a real image"
    with pytest.raises(UnsupportedFormatError):
        FileDetector.analyze_file(fake_png_bytes, "spoofed.png")

def test_file_detector_oversize(monkeypatch):
    monkeypatch.setattr(FileDetector, "MAX_FILE_SIZE_MB", 0.000001) # 1 byte
    with pytest.raises(FileSizeError):
        FileDetector.analyze_file(b"larger than 1 byte", "test.txt")

def test_adapter_registry():
    AdapterManager.register_adapter(["image/png"], ImageAdapter)
    adapter = AdapterManager.get_adapter("image/png")
    assert isinstance(adapter, ImageAdapter)
    
    with pytest.raises(ValueError):
        AdapterManager.get_adapter("video/quicktime")

def test_image_adapter():
    # Setup
    AdapterManager.register_adapter(["image/png"], ImageAdapter)
    image_bytes = create_synthetic_image()
    metadata = FileDetector.analyze_file(image_bytes, "test.png")
    
    # Parse
    adapter = ImageAdapter()
    cdo = adapter.parse(image_bytes, metadata)
    
    # Verify CDO structure
    assert isinstance(cdo, CommonDocumentObject)
    assert cdo.filename == "test.png"
    assert cdo.mime_type == "image/png"
    assert cdo.modality == "image"
    assert len(cdo.images) > 0 or len(cdo.extracted_assets) > 0

def test_ingestion_engine_flow():
    # Full flow
    image_bytes = create_synthetic_image()
    # Ingest
    result = IngestionEngine.ingest_file(image_bytes, "engine_test.png")
    
    if hasattr(result, '__iter__') and not isinstance(result, CommonDocumentObject):
        result = next(result)
        
    assert result.filename == "engine_test.png"
    assert result.fingerprint is not None

def test_resource_manager():
    metrics = resource_manager.get_system_metrics()
    assert "ram_percent" in metrics
    assert "cpu_percent" in metrics
    
    # Force a mock high RAM state
    resource_manager.memory_threshold_percent = 0.0 
    assert resource_manager.should_stream(100) == True
    
    # Reset
    resource_manager.memory_threshold_percent = 100.0
    assert resource_manager.should_stream(100) == False

def test_resource_manager_batch_size(monkeypatch):
    # Mock get_system_metrics
    def mock_metrics_low():
        return {"cpu_percent": 10.0, "ram_percent": 95.0, "ram_available_gb": 0.3} # Low RAM
        
    def mock_metrics_normal():
        return {"cpu_percent": 10.0, "ram_percent": 50.0, "ram_available_gb": 1.5} # Normal RAM
        
    def mock_metrics_high():
        return {"cpu_percent": 10.0, "ram_percent": 20.0, "ram_available_gb": 8.0} # High RAM

    # Test Low RAM
    monkeypatch.setattr(resource_manager, "get_system_metrics", mock_metrics_low)
    assert resource_manager.get_batch_size() == 1
    
    # Test Normal RAM
    monkeypatch.setattr(resource_manager, "get_system_metrics", mock_metrics_normal)
    assert resource_manager.get_batch_size() == 5
    
    # Test High RAM
    monkeypatch.setattr(resource_manager, "get_system_metrics", mock_metrics_high)
    assert resource_manager.get_batch_size() == 10
