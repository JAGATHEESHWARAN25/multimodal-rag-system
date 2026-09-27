import pytest
from app.core.ingestion.adapters.csv_adapter import CSVAdapter
from app.core.pipeline.orchestrator import PipelineOrchestrator

def test_csv_adapter_comma_delimiter():
    adapter = CSVAdapter()
    csv_bytes = b"Server,IP,Role\nAUTH-SRV-01,10.0.0.15,Authentication\nDB-CLUSTER-A,10.0.0.22,Database"
    cdo = adapter.parse(csv_bytes, {"filename": "servers.csv", "mime_type": "text/csv"})
    
    assert cdo.modality == "CSV"
    table = cdo.pages[0]["elements"][0]
    assert table["type"] == "table"
    assert table["headers"] == ["Server", "IP", "Role"]
    assert len(table["rows"]) == 2
    assert table["rows"][0]["cells"][0]["text"] == "AUTH-SRV-01"

def test_csv_adapter_semicolon_delimiter():
    adapter = CSVAdapter()
    csv_bytes = b"Host;IP;Status\nGATEWAY-01;10.0.0.1;ACTIVE\n"
    cdo = adapter.parse(csv_bytes, {"filename": "gateway.csv", "mime_type": "text/csv"})
    
    table = cdo.pages[0]["elements"][0]
    assert table["formatting"]["delimiter"] == ";"
    assert table["headers"] == ["Host", "IP", "Status"]

def test_csv_orchestration_and_chroma():
    adapter = CSVAdapter()
    csv_bytes = b"Host,IP\nAUTH-SRV-01,10.0.0.15\n"
    cdo = adapter.parse(csv_bytes, {"filename": "inv.csv"})
    schema, chunks = PipelineOrchestrator.process_document(cdo)
    
    assert schema.source_file == "inv.csv"
    assert any(c["metadata"].get("column_name") == "Host" for c in chunks if "metadata" in c)
