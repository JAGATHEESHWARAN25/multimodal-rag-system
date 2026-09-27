# Universal Multimodal Query & Related Knowledge — Pre-Implementation Inspection Audit

**Date**: August 11, 2026  
**System Baseline**: 73/73 Backend Tests Passed | 26/26 Frontend Tests Passed | 100% Offline Air-Gapped

---

## 1. Codebase Reality & Inspection Findings

### A. What Already Exists & Works
1. **Multi-Format Ingestion**: `IngestionEngine` with `ImageAdapter`, `PDFAdapter`, `DOCXAdapter`, `PPTXAdapter` producing `CommonDocumentObject` (CDO).
2. **Vision & Layout Processing**: `PipelineOrchestrator` combining Tesseract/PaddleOCR, Florence-2 layout analysis (`VisionPipeline`), entity extraction (`AdvancedLocalEntityExtractor`), `UniversalKnowledgeSchema` generation, and `SemanticChunker`.
3. **Database Architecture**: SQLite tables (`documents`, `background_jobs`, `knowledge_objects`, `relationship_edges`, `chat_sessions`, `chat_messages`, `audit_logs`, `vision_cache`, `processing_history`).
4. **Graph Traversal**: `SQLiteGraphStore` + `GraphManager` + `GraphReasoningEngine` supporting multi-hop BFS (`find_neighbors`, `find_path`, `find_related_entities`, `find_parent_documents`).
5. **Vector Index**: ChromaDB `document_chunks` collection indexed via `LocalEmbeddingsCalculator` (768-dim TF-IDF / SentenceTransformer).
6. **RBAC Security**: `UserContext`, `Role`, `AccessClassification`, `authorize_document_classification()`.
7. **Scoring & Multi-Agent RAG**: `EvidenceScorer` and 6-stage `ModularMultiAgentPipeline`.
8. **Frontend SPA**: React/Vite dashboard, upload modal, document gallery, inspector with OCR/bounding-box overlays, graph visualizer, and SSE streaming chat.

### B. What Is Missing / Needs Closure
1. **Knowledge Graph Object Persistence**: `PipelineOrchestrator` creates `KnowledgeObject` blocks and `RelationshipEdge` objects during document processing, but does not batch insert them into SQLite `knowledge_objects` and `relationship_edges` tables via `db_manager`.
2. **Universal Multimodal Query Service**: No unified service (`UniversalMultimodalQueryService` in `backend/app/core/rag/universal_query.py`) to coordinate input attachment resolution, input summary generation, hybrid vector + graph + entity discovery, pre-LLM RBAC filtering, and structured response construction.
3. **Chat Endpoint Multimodal Extension**: `ChatRequest` in `backend/app/api/rag.py` lacks `file_ids: Optional[List[str]]` and does not emit SSE events for `input_summary`, `related_knowledge`, and `confidence`. Line 290 has a variable scoping bug (`citations` vs `rag_result["citations"]`).
4. **Frontend Multimodal Input & Rich Cards**: Chat UI in `App.jsx` lacks a multi-file attachment selector and does not render Input Summary, Confidence Badges, Related Documents (with click-to-view), Related Images (with thumbnails), Entity Tags, or Graph Relationships.

---

## 2. File Change Plan

### Files That Will Change
- `backend/app/models/database.py`: Add `save_knowledge_objects()`, `save_relationship_edges()`, `get_knowledge_objects_by_document()`, and query helpers.
- `backend/app/core/pipeline/orchestrator.py`: Invoke `save_knowledge_objects()` and `save_relationship_edges()` during document processing.
- `backend/app/api/rag.py`: Extend `ChatRequest` schema, update SSE streaming protocol, fix scoping bug on line 290.
- `backend/app/core/rag/agents.py`: Integrate input document context into multi-agent pipeline.
- `frontend/src/App.jsx`: Add file attachment UI, handle multi-file chat query submission, render rich response components (Input Summary, Confidence, Citations, Related Docs, Related Images, Entities, Graph).
- `frontend/src/__tests__/App.test.jsx`: Add Vitest tests for attachment UI and rich response rendering.

### Files That Must NOT Change Architecture / Contracts
- `backend/app/core/security.py` (Must preserve `authorize_document_classification()` semantics)
- `backend/app/core/ingestion/engine.py` (Ingestion pipeline contract must remain untouched)
- `backend/app/core/graph/store.py` (`SQLiteGraphStore` interface must remain intact)

---

## 3. New Files To Be Created
- `backend/app/core/rag/universal_query.py`: `UniversalMultimodalQueryService` implementation and Pydantic models.
- `backend/tests/test_universal_multimodal_query.py`: Comprehensive backend test suite (24+ assertions).
- `backend/docs/universal_multimodal_query_validation_report.md`: Final completion & performance validation report.

---

## 4. Risks & Regression Mitigation Strategy
1. **RBAC Information Leakage**: Perform `authorize_document_classification()` on EVERY candidate object before LLM context construction or response rendering.
2. **CPU Execution Latency**: Reuse `DocumentFingerprinter` SHA-256 cache for already-indexed attachments. Cap graph traversal at max depth 3.
3. **Frontend Regression**: Keep existing chat state structures intact so standard text-only chat sessions function without disruption.
