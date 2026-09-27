import pytest
from app.core.nlp.entity_extractor import EntityExtractor

def test_entity_extractor():
    text = "John called on 15-Aug-2023. He works for Microsoft Corp and earns $1,000,000. Contact: admin@ntro.gov.in or 555-123-4567. Reference DOC-99X."
    
    entities = EntityExtractor.extract_entities(text)
    
    types = {e["type"]: e["value"] for e in entities}
    
    assert "DATE" in types
    assert types["DATE"] == "15-Aug-2023"
    
    assert "ORGANIZATION" in types
    assert types["ORGANIZATION"] == "Microsoft Corp"
    
    assert "MONEY" in types
    assert types["MONEY"] == "$1,000,000"
    
    assert "EMAIL" in types
    assert types["EMAIL"] == "admin@ntro.gov.in"
    
    assert "PHONE" in types
    assert types["PHONE"] == "555-123-4567"
    
    assert "DOCUMENT_ID" in types
    assert types["DOCUMENT_ID"] == "DOC-99X"
