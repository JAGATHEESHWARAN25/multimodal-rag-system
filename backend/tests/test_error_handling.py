import pytest
from app.core.ingestion.detector import FileDetector, CorruptedFileError, FileValidationError

def test_empty_file_fails():
    with pytest.raises(FileValidationError):
        FileDetector.analyze_file(b"", "empty.txt")
        
def test_unsupported_file_fails():
    from app.core.ingestion.detector import UnsupportedFormatError
    with pytest.raises(UnsupportedFormatError):
        # Fallback to random byte signature not matching
        FileDetector.analyze_file(b"\x00\x01\x02\x03\x04\x05\x06\x07", "random.dat")

def test_corrupted_pdf_fails():
    from app.core.ingestion.adapters.pymupdf_engine import PyMuPDFEngine
    engine = PyMuPDFEngine()
    with pytest.raises(CorruptedFileError):
        engine.open_document(b"this is not a valid pdf document at all")
