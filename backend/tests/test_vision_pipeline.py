import pytest
import numpy as np
from app.core.vision.pipeline import VisionPipeline
from app.core.model_manager import model_manager
from app.core.vision.engines.mock import MockVisionEngine

@pytest.fixture(autouse=True)
def setup_models():
    model_manager.register_model_class("vlm", "mock_vlm", MockVisionEngine, {"model_id": "mock_vlm"})
    # Ensure it's loaded
    model_manager.get_model("vlm", "mock_vlm")
    yield
    model_manager.unload_all()

def test_vision_pipeline_mock():
    # Create a dummy image
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    
    pipeline = VisionPipeline(mock_vlm=True)
    blocks, relationships = pipeline.process_visual_asset(
        image=image, 
        parent_document_id="doc_123", 
        parent_page_id="page_123", 
        page_number=1
    )
    
    # We mocked 3 regions: figure, table, text
    # figure -> creates 1 KO (chart) + 1 Rel
    # table -> creates 1 KO (table) + 1 Rel, PLUS 4 cells + 4 Rels
    # text -> creates 1 KO (text) + 1 Rel
    # Total Blocks = 1 + (1+4) + 1 = 7
    # Total Rels = 1 + (1+4) + 1 = 7
    
    assert len(blocks) == 7, f"Expected 7 blocks, got {len(blocks)}"
    assert len(relationships) == 7, f"Expected 7 rels, got {len(relationships)}"
    
    block_types = [b.block_type for b in blocks]
    assert "table" in block_types
    assert "table_cell" in block_types
    assert "chart" in block_types
    assert "text" in block_types
    
    # Check relationships
    for rel in relationships:
        if rel.relationship_type == "CHILD_OF":
            # Target should be either the page or the table
            assert rel.target_id == "page_123" or rel.target_id in [b.knowledge_object_id for b in blocks if b.block_type == "table"]

def test_cache_hits():
    pipeline = VisionPipeline(mock_vlm=True)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # First run (miss)
    blocks1, rels1 = pipeline.process_visual_asset(img, "doc_123", "page_123", 1)
    
    # Second run (hit)
    blocks2, rels2 = pipeline.process_visual_asset(img, "doc_123", "page_123", 1)
    
    assert len(blocks1) == len(blocks2)
    assert len(rels1) == len(rels2)
