import pytest
from app.core.security import UserContext, Role, AccessClassification, authorize_document_classification
from app.models.database import db_manager
from app.core.rag.universal_query import UniversalMultimodalQueryService
from app.core.ingestion.engine import IngestionEngine
from app.core.pipeline.orchestrator import PipelineOrchestrator

def test_rbac_boundary_pre_llm_filtering():
    viewer_ctx = UserContext(id="v1", username="viewer", role=Role.VIEWER)
    analyst_ctx = UserContext(id="a1", username="analyst", role=Role.INTELLIGENCE_ANALYST)
    admin_ctx = UserContext(id="ad1", username="admin", role=Role.SYSTEM_ADMIN)

    # VIEWER cannot access SECRET
    with pytest.raises(Exception):
        authorize_document_classification(viewer_ctx, "SECRET")

    # ANALYST and ADMIN can access SECRET
    authorize_document_classification(analyst_ctx, "SECRET")
    authorize_document_classification(admin_ctx, "SECRET")

def test_knowledge_graph_objects_and_edges_persistence():
    doc_id = "test_doc_persistence_123"
    kos = [
        {
            "knowledge_object_id": "ko_1",
            "parent_document_id": doc_id,
            "block_type": "heading",
            "content": "Secret Radar Specifications",
            "bounding_box": [10, 20, 100, 200],
            "metadata": {"classification": "SECRET"}
        },
        {
            "knowledge_object_id": "ko_2",
            "parent_document_id": doc_id,
            "block_type": "entity",
            "content": "Radar Array X1",
            "metadata": {"entity_type": "TECHNOLOGY"}
        }
    ]
    edges = [
        {
            "id": "edge_1",
            "source_id": "ko_1",
            "target_id": "ko_2",
            "relationship_type": "MENTIONS"
        }
    ]

    # Save to SQLite
    db_manager.save_knowledge_objects(kos)
    db_manager.save_relationship_edges(edges)

    # Verify retrieval
    retrieved_kos = db_manager.get_knowledge_objects_by_document(doc_id)
    assert len(retrieved_kos) == 2
    assert retrieved_kos[0]["content"] == "Secret Radar Specifications"
    assert retrieved_kos[0]["bounding_box"] == [10, 20, 100, 200]

def test_universal_multimodal_query_service_text_only():
    user_ctx = UserContext(id="u1", username="testuser", role=Role.SYSTEM_ADMIN)
    res = UniversalMultimodalQueryService.execute_query(
        query="What is the architecture of the system?",
        user_context=user_ctx,
        limit=3
    )

    assert "trace_id" in res
    assert "input_summary" in res
    assert "evidence_confidence" in res
    assert "citations" in res
    assert "related_documents" in res
    assert "related_images" in res
    assert "related_entities" in res
    assert "relationships" in res
    assert "answer_stream" in res

def test_universal_multimodal_query_service_with_attachments(tmp_path):
    # Ingest a dummy image
    import cv2
    import numpy as np
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.putText(img, "NTRO Test Diagram", (5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    _, img_bytes = cv2.imencode(".png", img)

    cdo = IngestionEngine.ingest_file(img_bytes.tobytes(), "test_diagram.png")
    schema, chunks = PipelineOrchestrator.process_document(cdo)

    # Register in DB
    doc_data = {
        "id": schema.document_id,
        "sha256_hash": schema.sha256_hash,
        "filename": "test_diagram.png",
        "mime_type": "image/png",
        "modality": "image",
        "processing_profile": "default",
        "status": "READY",
        "owner_id": "u1",
        "classification": "PUBLIC"
    }
    db_manager.save_document(doc_data)

    user_ctx = UserContext(id="u1", username="testuser", role=Role.SYSTEM_ADMIN)
    res = UniversalMultimodalQueryService.execute_query(
        query="Identify the components in this diagram and list related assets",
        user_context=user_ctx,
        file_ids=[schema.document_id],
        limit=3
    )

    assert "test_diagram.png" in res["input_summary"]
    assert len(res["input_objects"]) == 1
    assert res["input_objects"][0]["document_id"] == schema.document_id
