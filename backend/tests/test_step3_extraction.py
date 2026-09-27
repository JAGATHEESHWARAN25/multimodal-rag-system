import pytest
from app.core.nlp.base_entity_extractor import BaseEntityExtractor
from app.core.nlp.entity_extractor import RuleBasedEntityExtractor
from app.core.nlp.advanced_entity_extractor import AdvancedLocalEntityExtractor
from app.core.ingestion.table_extractor import BaseTableExtractor, NativeTableExtractor, AdvancedTableExtractor

def test_entity_extractor_abstractions():
    rule_ext = RuleBasedEntityExtractor()
    adv_ext = AdvancedLocalEntityExtractor()

    assert isinstance(rule_ext, BaseEntityExtractor)
    assert isinstance(adv_ext, BaseEntityExtractor)

    sample_text = "SECRET document from Ministry of Defence in New Delhi dated 12th Jan 2026. Contact test@example.com or DOC-9912."
    
    entities = adv_ext.extract_entities(sample_text)
    types = [e["type"] for e in entities]

    assert "CLASSIFICATION_MARKING" in types
    assert "LOCATION" in types
    assert "ORGANIZATION" in types
    assert "EMAIL" in types
    assert "DOCUMENT_ID" in types

def test_table_extractor_abstractions():
    native_tbl = NativeTableExtractor()
    adv_tbl = AdvancedTableExtractor()

    assert isinstance(native_tbl, BaseTableExtractor)
    assert isinstance(adv_tbl, BaseTableExtractor)

    sample_doc = [
        {"type": "table", "headers": ["Name", "Role"], "rows": [["Alice", "Officer"], ["Bob", "Analyst"]]}
    ]

    res = adv_tbl.extract_tables(sample_doc)
    assert len(res) == 1
    assert "markdown" in res[0]
    assert "| Alice | Officer |" in res[0]["markdown"]
