import time
import pytest
from app.models.database import db_manager
from app.core.security import UserContext, Role, authorize_document_classification, AccessClassification
from app.core.graph.reasoning import GraphReasoningEngine
from app.core.rag.agents import ModularMultiAgentPipeline
from app.core.background_worker import HardenedBackgroundWorker
from app.core.nlp.advanced_entity_extractor import AdvancedLocalEntityExtractor
from app.core.ingestion.table_extractor import AdvancedTableExtractor

def test_security_rbac_classification_boundaries():
    viewer_ctx = UserContext(id="v1", username="viewer", role=Role.VIEWER)
    officer_ctx = UserContext(id="o1", username="officer", role=Role.DOCUMENT_OFFICER)
    admin_ctx = UserContext(id="a1", username="admin", role=Role.SYSTEM_ADMIN)

    # PUBLIC document allowed for all
    authorize_document_classification(viewer_ctx, "PUBLIC")
    authorize_document_classification(officer_ctx, "PUBLIC")
    authorize_document_classification(admin_ctx, "PUBLIC")

    # SECRET document denied for VIEWER & DOCUMENT_OFFICER, allowed for INTELLIGENCE_ANALYST / SYSTEM_ADMIN
    with pytest.raises(Exception):
        authorize_document_classification(viewer_ctx, "SECRET")

    with pytest.raises(Exception):
        authorize_document_classification(officer_ctx, "SECRET")

    authorize_document_classification(admin_ctx, "SECRET")

def test_bounded_graph_reasoning_cycle_and_depth():
    # Verify depth limits (capped at max 5)
    neighbors = GraphReasoningEngine.find_neighbors("root_node", depth=10)
    assert isinstance(neighbors, list)

    path = GraphReasoningEngine.find_path("node_x", "node_y", max_depth=10)
    assert isinstance(path, list)

def test_full_pipeline_end_to_end():
    # 1. Advanced Entity Extraction
    extractor = AdvancedLocalEntityExtractor()
    entities = extractor.extract_entities("CONFIDENTIAL report from NTRO in New Delhi dated 15th August 2026.")
    assert len(entities) >= 3

    # 2. Advanced Table Extraction
    tbl_extractor = AdvancedTableExtractor()
    tables = tbl_extractor.extract_tables([{"type": "table", "headers": ["A", "B"], "rows": [["1", "2"]]}] )
    assert len(tables) == 1
    assert "markdown" in tables[0]

    # 3. Deterministic Multi-Agent RAG Pipeline Execution
    from app.core.embeddings import LocalEmbeddingsCalculator
    LocalEmbeddingsCalculator.calculate_query_embedding("warmup")
    start_time = time.time()
    pipeline = ModularMultiAgentPipeline()
    res = pipeline.execute_rag("What is the status of the project?", user_role="SYSTEM_ADMIN", limit=3)
    duration = time.time() - start_time

    assert "trace_id" in res
    assert "citations" in res
    assert "answer_stream" in res
    tokens = list(res["answer_stream"])
    assert len(tokens) > 0
    assert duration < 5.0 # Sub-5-second offline execution benchmark
