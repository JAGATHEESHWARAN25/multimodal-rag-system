import pytest
import os
import fitz
from app.core.ingestion.detector import FileDetector, CorruptedFileError
from app.core.ingestion.adapters.manager import AdapterManager
from app.core.ingestion.adapters.pdf_adapter import PDFAdapter
from app.core.ingestion.adapters.pymupdf_engine import PyMuPDFEngine
from app.models.schema import CommonDocumentObject
from app.core.resource_manager import resource_manager

def create_synthetic_pdf(filepath: str, text: str = "Hello PDF", pages: int = 1):
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text(fitz.Point(50, 50), text)
    doc.save(filepath)
    doc.close()

@pytest.fixture
def temp_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    create_synthetic_pdf(str(pdf_path), pages=3)
    yield str(pdf_path)
    if pdf_path.exists():
        os.remove(pdf_path)

def test_pymupdf_engine_metadata(temp_pdf):
    with open(temp_pdf, "rb") as f:
        file_bytes = f.read()
        
    engine = PyMuPDFEngine()
    doc = engine.open_document(file_bytes)
    assert engine.get_page_count(doc) == 3
    
    metadata = engine.get_metadata(doc)
    assert not metadata["is_encrypted"]
    
    engine.close_document(doc)

def test_pymupdf_engine_text(temp_pdf):
    with open(temp_pdf, "rb") as f:
        file_bytes = f.read()
        
    engine = PyMuPDFEngine()
    doc = engine.open_document(file_bytes)
    
    page_data = engine.extract_page_data(doc, 0, render_images=False)
    assert "Hello PDF" in page_data["text_blocks"][0]
    
    engine.close_document(doc)

def test_pdf_adapter_streaming(temp_pdf):
    # Register
    AdapterManager.register_adapter(["application/pdf"], PDFAdapter)
    
    with open(temp_pdf, "rb") as f:
        file_bytes = f.read()
        
    metadata = FileDetector.analyze_file(file_bytes, "test.pdf")
    
    # Force batch size 2 for streaming test
    resource_manager.memory_threshold_percent = 0.0 # forces high memory state -> batch 1
    # Wait, the logic is: if ram_percent > threshold or ram < 500, return 1
    
    adapter = PDFAdapter()
    generator = adapter.parse(file_bytes, metadata)
    
    chunks = list(generator)
    
    # Reset resource manager
    resource_manager.memory_threshold_percent = 85.0
    
    # Should have yielded multiple chunks since it's 3 pages
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, CommonDocumentObject)
        assert chunk.modality == "pdf"
    assert chunk.filename == "test.pdf"

def test_pdf_adapter_corrupted():
    bad_bytes = b"%PDF-1.4\n%EOF\n" * 10
    engine = PyMuPDFEngine()
    with pytest.raises(CorruptedFileError):
        engine.open_document(bad_bytes)
