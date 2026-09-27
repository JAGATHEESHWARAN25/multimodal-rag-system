import pytest
from app.models.schema import CommonDocumentObject, UniversalKnowledgeSchema
from app.core.pipeline.orchestrator import PipelineOrchestrator

def test_pipeline_relationships():
    # Construct a minimal CDO simulating PDF Adapter output
    cdo = CommonDocumentObject(
        document_id="doc_xyz",
        fingerprint="abcd",
        modality="pdf",
        filename="test.pdf",
        mime_type="application/pdf",
        pages=[
            {
                "page_num": 0,
                "text_blocks": ["Paragraph 1", "Paragraph 2"],
                "tables": [{"rows": 2}]
            }
        ]
    )
    
    schema, chunks = PipelineOrchestrator.process_document(cdo)
    
    assert isinstance(schema, UniversalKnowledgeSchema)
    assert len(schema.relationships) > 0
    
    # 1 page + 2 text_blocks + 1 table = 4 KOs
    assert len(schema.semantic_blocks) == 4
    
    page_kos = [b for b in schema.semantic_blocks if b.block_type == "page"]
    assert len(page_kos) == 1
    page_id = page_kos[0].knowledge_object_id
    
    for rel in schema.relationships:
        assert rel.relationship_type == "CHILD_OF"
        assert rel.target_id == page_id
        
def test_pipeline_vision_relationships():
    import numpy as np
    from unittest.mock import patch
    from app.core.vision.pipeline import VisionPipeline
    cdo = CommonDocumentObject(
        document_id="doc_img",
        fingerprint="img123",
        modality="image",
        filename="test.png",
        mime_type="image/png",
        images=[np.zeros((100, 100, 3), dtype=np.uint8)]
    )
    
    mock_vp = VisionPipeline(mock_vlm=True)
    with patch("app.core.pipeline.orchestrator.VisionPipeline", return_value=mock_vp):
        schema, chunks = PipelineOrchestrator.process_document(cdo)
    
    # page KO + vision pipeline KOs (7 from mock) = 8
    assert len(schema.semantic_blocks) == 8
    page_kos = [b for b in schema.semantic_blocks if b.block_type == "page"]
    assert len(page_kos) == 1
    page_id = page_kos[0].knowledge_object_id
    
    assert any(rel.target_id == page_id for rel in schema.relationships)
