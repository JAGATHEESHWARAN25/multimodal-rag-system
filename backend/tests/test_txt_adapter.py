import pytest
from app.core.ingestion.adapters.txt_adapter import TXTAdapter
from app.core.pipeline.orchestrator import PipelineOrchestrator
from app.core.chunking import SemanticChunker

def test_txt_adapter_basic():
    adapter = TXTAdapter()
    content = b"# TITLE\nThis is paragraph one.\n\nThis is paragraph two."
    cdo = adapter.parse(content, {"filename": "test.txt", "mime_type": "text/plain"})
    
    assert cdo.modality == "TXT"
    assert cdo.filename == "test.txt"
    assert len(cdo.pages[0]["elements"]) == 3
    assert cdo.pages[0]["elements"][0]["type"] == "heading"
    assert cdo.pages[0]["elements"][1]["type"] == "paragraph"

def test_txt_adapter_utf8_bom():
    adapter = TXTAdapter()
    content = "\ufeff# BOM TITLE\nBOM text content.".encode("utf-8-sig")
    cdo = adapter.parse(content, {"filename": "bom.txt", "mime_type": "text/plain"})
    
    assert cdo.pages[0]["elements"][0]["text"] == "BOM TITLE"

def test_txt_adapter_binary_rejection():
    adapter = TXTAdapter()
    binary_content = b"Some text\x00\x00\x00Binary Data"
    with pytest.raises(ValueError, match="binary null bytes"):
        adapter.parse(binary_content, {"filename": "fake.txt"})

def test_txt_orchestration_and_entities():
    adapter = TXTAdapter()
    content = b"# OPERATION COMMAND\nContact Officer at NTRO Department (EMAIL: a.thorne@ntro.gov, Date: Jan 2026)."
    cdo = adapter.parse(content, {"filename": "op_test_unique.txt"})
    schema, chunks = PipelineOrchestrator.process_document(cdo)
    
    assert schema.source_file == "op_test_unique.txt"
    assert len(chunks) > 0
    # Verify entity extraction
    entities = [b for b in schema.semantic_blocks if b.block_type == "entity"]
    assert len(entities) > 0
