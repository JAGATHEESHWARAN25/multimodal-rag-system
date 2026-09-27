# Universal Multimodal Query & Related Knowledge — Technical Codebase Audit

**Date**: August 11, 2026  
**System Baseline**: 73/73 Backend Pytest Passed | 26/26 Frontend Vitest Passed | 100% Offline Air-Gapped Architecture

---

## 1. Existing Functionality

The platform already possesses a robust, offline-first multimodal RAG foundation:

1. **Unified Ingestion & Adapters** (`backend/app/core/ingestion/`):
   - `IngestionEngine` detects mime-types/extensions and routes inputs through `ImageAdapter`, `PDFAdapter`, `DOCXAdapter`, and `PPTXAdapter`.
   - Normalizes input documents into `CommonDocumentObject` (CDO) with support for text blocks, tables, images, slides, shapes, and metadata.
2. **Pipeline Processing & Vision Intelligence** (`backend/app/core/pipeline/`, `backend/app/core/vision/`):
   - `PipelineOrchestrator.process_document()` coordinates fingerprinting (`DocumentFingerprinter`), quality analysis (`ImageQualityAnalyzer`), classification (`DocumentClassifier`), OCR (Tesseract / PaddleOCR), Florence-2 vision analysis (`VisionPipeline`), entity extraction (`AdvancedLocalEntityExtractor`), `UniversalKnowledgeSchema` generation, and semantic chunking (`SemanticChunker`).
3. **Canonical Persistence & Graph Store** (`backend/app/models/database.py`, `backend/app/core/graph/`):
   - SQLite tables: `documents`, `background_jobs`, `knowledge_objects`, `relationship_edges`, `chat_sessions`, `chat_messages`, `audit_logs`, `vision_cache`, `processing_history`.
   - `SQLiteGraphStore` + `GraphManager` + `GraphReasoningEngine` for bounded multi-hop BFS graph traversal, pathfinding, and entity relationships.
4. **Vector Retrieval & Fingerprint Cache** (`backend/app/core/vectordb.py`, `backend/app/core/embeddings.py`):
   - Local ChromaDB collection `document_chunks` queried via `LocalEmbeddingsCalculator` (768-dim TF-IDF / SentenceTransformer vector representation).
   - SHA-256 fingerprinting prevents re-indexing of duplicate files.
5. **Security & RBAC Layer** (`backend/app/core/security.py`):
   - Roles: `SYSTEM_ADMIN`, `INTELLIGENCE_ANALYST`, `DOCUMENT_OFFICER`, `REVIEWER`, `VIEWER`.
   - Classifications: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `SECRET`.
   - Centralized enforcement via `authorize_document_classification(user_context, doc_classification)`.
6. **Deterministic Multi-Stage RAG Pipeline** (`backend/app/core/rag/agents.py`):
   - 6-stage single-pass execution: `QueryPlanner` → `RetrievalAgent` → `GraphAgent` → `EvidenceAgent` → `AnswerAgent` → `CitationAgent`.
   - Evidence scoring via `EvidenceScorer.calculate_confidence()`.
7. **Frontend Architecture** (`frontend/src/App.jsx`):
   - React + Vite SPA featuring Dashboard, Document Upload, Document Gallery, Document Inspector Modal (with OCR & bounding box overlay), Graph Visualization, and Chat Interface with SSE token streaming.

---

## 2. Missing Functionality

1. **Multimodal File Attachment in Chat**:
   - The `/api/chat` endpoint currently only accepts raw text queries (`query`) and session history. It cannot accept raw uploaded input files (PDF, DOCX, PPTX, images) attached directly to a prompt or a set of input document IDs.
2. **Unified Universal Multimodal Query Service**:
   - Missing `UniversalMultimodalQueryService` to coordinate:
     - On-the-fly ingestion of attached input files via `IngestionEngine`.
     - Generation of an **Input Summary / Understanding** for attached files.
     - Execution of **Related Knowledge Discovery** across vector space, graph edges, and entities.
     - Deterministic ranking of related authorized documents, related images, related entities, and graph relationships.
     - Pre-LLM RBAC filtering of all candidate context items.
     - Assembly of `UniversalMultimodalResponse`.
3. **Frontend Multimodal Chat Input & Rich Output Components**:
   - Chat UI in `App.jsx` lacks a multi-file attachment selector (PDF, DOCX, PPTX, image).
   - Chat message bubbles do not render Input Summaries, Evidence Confidence Badges, Related Documents (with click-to-view links), Related Images (with thumbnails), Related Entity Tags, or Interactive Graph Relationships.

---

## 3. Partially Implemented Functionality

1. **Knowledge Object & Graph Edge Persistence**:
   - `knowledge_objects` and `relationship_edges` SQLite tables exist, but `PipelineOrchestrator` currently returns schema in memory without calling a dedicated batch insert to `database.py` for graph nodes/edges during worker processing.
2. **Graph Reasoning for Discovery**:
   - `GraphReasoningEngine` provides `find_neighbors`, `find_path`, `find_related_entities`, and `find_parent_documents`, but these are not currently aggregated into a single Related Knowledge payload during chat responses.
3. **Chat Session Citations Storage**:
   - `/api/chat` references `citations_json` when saving messages, but line 290 has a minor scoping bug (`citations` vs `rag_result["citations"]`).

---

## 4. Reusable Code & Components

- `app.core.ingestion.engine.IngestionEngine` (Universal file ingestion)
- `app.core.pipeline.orchestrator.PipelineOrchestrator` (Feature extraction & vision pipeline)
- `app.core.graph.reasoning.GraphReasoningEngine` (Bounded graph traversal)
- `app.core.vectordb.VectorDatabaseManager` (Semantic vector search)
- `app.core.embeddings.LocalEmbeddingsCalculator` (Vector calculations)
- `app.core.rag.scoring.EvidenceScorer` (Confidence scoring)
- `app.core.security.authorize_document_classification` (RBAC filter)
- `app.core.audit.AuditLogger` (Audit trail logging)
- `app.core.llm_provider.LLMProviderFactory` (Local LLM abstraction)

---

## 5. Files Requiring Modification

1. `backend/app/models/database.py`: Add `save_knowledge_objects()` and `save_relationship_edges()` to persist graph nodes and edges to SQLite.
2. `backend/app/core/pipeline/orchestrator.py`: Ensure `save_knowledge_objects()` and `save_relationship_edges()` are called during document processing.
3. `backend/app/api/rag.py`: Update `ChatRequest` to accept `file_ids`, fix SSE streaming logic and line 290 scoping, emit new SSE events (`input_summary`, `related_knowledge`, `confidence`, `sources`, `token`).
4. `backend/app/core/rag/agents.py`: Integrate input document context & related knowledge into `ModularMultiAgentPipeline`.
5. `frontend/src/App.jsx`: Add file attachment UI to Chat, handle multi-file uploads, render Input Summary, Confidence Score, Related Documents, Related Images, Entity Tags, and Graph Relationships in chat messages.
6. `frontend/src/__tests__/App.test.jsx`: Add tests for multimodal chat submission and rich response rendering.

---

## 6. New Files Required

1. `backend/app/core/rag/universal_query.py`: Core `UniversalMultimodalQueryService` implementation and Pydantic response models.
2. `backend/docs/universal_multimodal_query_audit.md`: This technical audit document.
3. `backend/docs/universal_multimodal_query_implementation_plan.md`: Master implementation plan.
4. `backend/tests/test_universal_multimodal_query.py`: Comprehensive backend test suite.

---

## 7. API & Schema Changes Required

### API Endpoint Extensions
- **`POST /api/chat`**:
  - Accept optional `file_ids: List[str]` in request JSON.
  - Support multipart file upload or client pre-upload (`/api/upload`) prior to chat query.
  - Stream additional SSE event types:
    - `data: {"type": "input_summary", "summary": "..."}`
    - `data: {"type": "related_knowledge", "related_documents": [...], "related_images": [...], "related_entities": [...], "relationships": [...]}`
    - `data: {"type": "confidence", "confidence": {...}}`
    - `data: {"type": "sources", "sources": [...]}`
    - `data: {"type": "token", "text": "..."}`

### Schema Extensions
- `UniversalMultimodalResponse` model in `universal_query.py`:
  - `trace_id: str`
  - `answer: str`
  - `input_summary: str`
  - `evidence_confidence: Dict[str, Any]`
  - `citations: List[Dict[str, Any]]`
  - `related_documents: List[Dict[str, Any]]`
  - `related_images: List[Dict[str, Any]]`
  - `related_entities: List[Dict[str, Any]]`
  - `relationships: List[Dict[str, Any]]`
  - `input_objects: List[Dict[str, Any]]`

---

## 8. Frontend Changes Required

- Add file upload icon & attached file pill tags to Chat input box in `App.jsx`.
- Update SSE listener in `handleChatSubmit` to store `input_summary`, `related_knowledge`, `confidence`, and `sources` on the bot message state object.
- Render expandable card/section for:
  - **Input Summary**
  - **Confidence Badge** (`HIGH` / `MEDIUM` / `LOW` with score)
  - **Citations** (with clickable page/slide/bounding-box links to Inspector Modal)
  - **Related Documents** (with click to inspect)
  - **Related Images** (with thumbnail previews and modal view)
  - **Related Entities** (as styled tags)
  - **Graph Relationships** (formatted `Node → Relationship → Node` with button to open Graph view)

---

## 9. Database & Indexing Changes Required

- No new SQLite tables required. Existing `knowledge_objects`, `relationship_edges`, `documents`, `chat_messages`, `chat_sessions`, and `audit_logs` are sufficient.
- Add helper methods in `db_manager`:
  - `save_knowledge_objects(objects: List[dict])`
  - `save_relationship_edges(edges: List[dict])`
  - `get_knowledge_objects_by_document(document_id: str)`
  - `get_related_images_by_entities(entity_names: List[str])`

---

## 10. Risks & Regression Mitigation

1. **Performance Overhead on CPU**:
   - Processing new input files synchronously inside a chat query could cause HTTP timeouts if files are large.
   - *Mitigation*: Reuse cached CDO/schema via `DocumentFingerprinter`. Use fast-path text/structure extraction for uploaded query attachments. Limit LLM context size and enforce 30s pipeline timeout.
2. **RBAC Leakage via Graph Traversal**:
   - Traversing graph edges or entity links might expose titles or nodes belonging to `SECRET` documents to `VIEWER` users.
   - *Mitigation*: Perform strict `authorize_document_classification()` filtering on EVERY candidate related document, image, chunk, entity, and graph relationship before building the response or LLM context.
3. **Frontend Regression**:
   - Modifying `App.jsx` chat state could break existing chat session history loading.
   - *Mitigation*: Ensure backward compatibility for text-only messages and validate with full Vitest suite (`npm test`).
