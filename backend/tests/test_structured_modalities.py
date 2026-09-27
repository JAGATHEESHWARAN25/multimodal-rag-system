import pytest
from app.core.security import UserContext, Role, authorize_document_classification
from app.core.ingestion.detector import FileDetector, UnsupportedFormatError
from app.core.rag.universal_query import UniversalMultimodalQueryService
from app.core.cache.fingerprint import DocumentFingerprinter
from app.models.database import db_manager

def test_rbac_structured_modalities():
    viewer = UserContext(id="v1", username="viewer", role=Role.VIEWER)
    admin = UserContext(id="a1", username="admin", role=Role.SYSTEM_ADMIN)
    
    # VIEWER denied SECRET
    with pytest.raises(Exception):
        authorize_document_classification(viewer, "SECRET")
        
    # ADMIN allowed SECRET
    authorize_document_classification(admin, "SECRET")

def test_mime_spoofing_protection():
    fake_csv_bytes = b"%PDF-1.4 Fake PDF pretending to be CSV"
    with pytest.raises(UnsupportedFormatError):
        FileDetector.analyze_file(fake_csv_bytes, "spoofed.csv")

def test_cache_fingerprint_reuse():
    data = b"Host,IP\nAUTH-SRV-01,10.0.0.15\n"
    h1 = DocumentFingerprinter.generate_hash(data)
    h2 = DocumentFingerprinter.generate_hash(data)
    assert h1 == h2

def test_universal_multimodal_query_structured_integration():
    admin = UserContext(id="ad1", username="admin", role=Role.SYSTEM_ADMIN)
    
    res = UniversalMultimodalQueryService.execute_query(
        query="What is the IP address of AUTH-SRV-01 in the network inventory?",
        user_context=admin,
        limit=3
    )
    
    assert "trace_id" in res
    assert "answer_stream" in res
    assert "citations" in res
