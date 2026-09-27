import pytest
from app.core.rag.scoring import EvidenceScorer

def test_calculate_confidence():
    # 1. No evidence
    res = EvidenceScorer.calculate_confidence([])
    assert res["confidence"] == 0
    assert res["level"] == "NONE"
    
    # 2. High confidence: many good chunks from multiple docs
    matches = [
        {"score": 0.85, "metadata": {"document_id": "doc_1"}},
        {"score": 0.90, "metadata": {"document_id": "doc_1"}},
        {"score": 0.88, "metadata": {"document_id": "doc_2"}},
        {"score": 0.82, "metadata": {"document_id": "doc_3"}},
    ]
    res = EvidenceScorer.calculate_confidence(matches)
    assert res["confidence"] >= 80
    assert res["level"] == "HIGH"
    assert res["evidence_count"] == 4
    assert res["supporting_documents"] == 3
    
    # 3. Medium confidence: one single chunk of moderate score
    matches = [
        {"score": 0.60, "metadata": {"document_id": "doc_1"}}
    ]
    res = EvidenceScorer.calculate_confidence(matches)
    assert res["level"] == "MEDIUM"
    assert res["evidence_count"] == 1
    assert res["supporting_documents"] == 1

    # 4. Low confidence: mathematically distant, low count
    matches = [
        {"score": 0.25, "metadata": {"document_id": "doc_1"}}
    ]
    res = EvidenceScorer.calculate_confidence(matches)
    assert res["level"] == "LOW"
