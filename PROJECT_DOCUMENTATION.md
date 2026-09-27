# Multimodal Offline RAG System: Complete Repository & File Guide

**Document Version:** 1.0.0  
**Target Project:** Multimodal Offline Retrieval-Augmented Generation (RAG) System  
**Environment:** Air-Gapped / Offline On-Premise Secure Infrastructure (NTRO SIH25231)  
**Primary Tech Stack:** Python 3.10+ (FastAPI, PyMuPDF, python-docx, python-pptx, openpyxl, OpenCV, Tesseract OCR, Microsoft Florence-2, SentenceTransformers, ChromaDB, SQLite3, Ollama/Llama-3), React 18 (Vite, Vanilla CSS, Lucide-style UI, React Doc Viewer).

---

## 1. Executive Project Summary

The **Multimodal Offline RAG System** is an enterprise-grade, privacy-first, air-gapped document intelligence platform designed to process, index, and reason over multimodal documents (PDF, Word DOCX, PowerPoint PPTX, Excel XLSX, CSV, Plain Text, and Scanned Images/Screenshots) without sending any data over the public internet.

### Core Capabilities
1. **Multi-Format Ingestion:** Specialized modular adapters extract structured text, hierarchical headings, tables, embedded images, slide notes, formulas, and visual diagrams across 7+ file types.
2. **Advanced Document Vision Intelligence:** Integrates OpenCV image preprocessing (deskewing, binarization, CLAHE) with Tesseract OCR and Microsoft Florence-2 Vision-Language Model (VLM) for dense visual captioning, OCR bounding-box extraction, table structural parsing, and diagram understanding.
3. **Common Document Object (CDO) & Universal Knowledge Schema (UKS):** Normalizes diverse incoming file formats into structured, unified Knowledge Objects (KOs) connected by hierarchical and semantic relationship edges (`CHILD_OF`, `REFERENCES`, `CONNECTED_TO`).
4. **Knowledge Graph & Dual Vector Indexing:** Builds an on-disk SQLite knowledge graph coupled with ChromaDB dense vector indexing (using `BAAI/bge-base-en-v1.5` 768-dimensional embeddings) and keyword-boosted BM25-style scoring.
5. **Universal Query Engine & Multi-Agent RAG:** Decomposes complex user queries via specialized routing agents (`RoutingAgent`, `DocumentAgent`, `VisionAgent`, `SynthesisAgent`), performs hybrid vector + graph multi-hop retrieval, and streams answers word-by-word with token-level source citations and bounding-box highlighting.
6. **Enterprise Security & Role-Based Access Control (RBAC):** Implements a 5-tier classification model (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `SECRET`, `TOP_SECRET`) with JWT authentication, role hierarchies (`SYSTEM_ADMIN`, `INTELLIGENCE_ANALYST`, `DOCUMENT_OFFICER`, `AUDITOR`, `STANDARD_USER`), and an immutable tamper-evident audit trail.

---

## 2. High-Level System Architecture & Processing Pipeline

```mermaid
graph TD
    User([User / Analyst]) -->|HTTP / REST| Frontend[React + Vite Frontend]
    Frontend -->|Uploads / Queries| Gateway[FastAPI API Gateway]

    subgraph Backend Core
        Gateway --> Auth[Auth & RBAC Security Layer]
        Gateway --> UploadAPI[Upload & Ingestion Router]
        Gateway --> OCRAPI[OCR & Vision Router]
        Gateway --> RAGAPI[RAG & Universal Query Router]
        Gateway --> GraphAPI[Knowledge Graph Router]

        UploadAPI --> Worker[Hardened Background Worker]
        Worker --> Engine[Ingestion Engine & Detectors]
        Engine --> Adapters[Modality Adapters: PDF, DOCX, PPTX, XLSX, CSV, TXT, IMG]
        Adapters --> CDO[Common Document Object (CDO)]

        CDO --> Pipeline[Pipeline Orchestrator]
        Pipeline --> IQS[Image Quality & Preprocessing (OpenCV)]
        Pipeline --> VLM[Vision Pipeline (Florence-2 / Tesseract)]
        Pipeline --> UKS[Universal Knowledge Schema (UKS)]
        Pipeline --> GraphStore[(SQLite Knowledge Graph)]
        Pipeline --> Chunker[Semantic Chunker]
        Chunker --> Embedder[SentenceTransformers Embeddings]
        Embedder --> VectorDB[(ChromaDB Vector Store)]

        RAGAPI --> QueryEngine[Universal Query Engine]
        QueryEngine --> MultiAgent[Multi-Agent Router]
        MultiAgent --> VectorDB
        MultiAgent --> GraphStore
        MultiAgent --> Ollama[Local Ollama / Llama 3 LLM]
        Ollama -->|Streaming SSE Tokens| Frontend
    end
```

---

## 3. Directory Structure Overview

```
Multimodal RAG System/
├── README.md                               # Setup, installation, and usage instructions
├── PROJECT_DOCUMENTATION.md                # Complete system & file documentation
├── benchmark.py                            # End-to-end pipeline latency & memory benchmark
├── build_nyayaai_format_paper.py           # Generates IEEE publication paper (DOCX/PDF)
├── extract_fonts.py                        # PDF font metadata extractor utility
├── run_custom_tests.py                     # Custom regression & adapter runner
├── Multimodal_Offline_RAG_IEEE_Paper.docx  # Generated IEEE conference research paper
├── Multimodal_Offline_RAG_IEEE_Paper.pdf   # Generated IEEE conference paper in PDF format
├── Multimodal_Offline_RAG_Review2.pptx     # Milestone Review-2 slide deck
├── Review_2_Functional_Verification_Guide.pdf # Verification manual for evaluations
│
├── backend/                                # FastAPI Python Backend
│   ├── .env                                # Local environment variables
│   ├── requirements.txt                    # Python package dependencies
│   ├── app/
│   │   ├── config.py                       # Global settings & storage path resolution
│   │   ├── main.py                         # FastAPI application entrypoint & lifespans
│   │   ├── api/                            # REST API Route Handlers
│   │   │   ├── auth.py                     # Authentication, JWT, user management
│   │   │   ├── graph.py                    # Knowledge Graph traversal & visualization
│   │   │   ├── ocr.py                      # OCR extraction & cache endpoints
│   │   │   ├── rag.py                      # Search, streaming chat, and chat sessions
│   │   │   ├── summarize.py                # Hierarchical document summarization
│   │   │   ├── system.py                   # System health, metrics & audit logs
│   │   │   └── upload.py                   # File uploads, document retrieval & deletion
│   │   ├── core/                           # Internal processing engines & utilities
│   │   │   ├── audit.py                    # Structured security audit logging
│   │   │   ├── background_worker.py        # Resilient SQLite task worker loop
│   │   │   ├── chunking.py                 # Semantic chunking engine
│   │   │   ├── embeddings.py               # Local SentenceTransformer embeddings
│   │   │   ├── events.py                   # Pub/Sub event bus for pipeline hooks
│   │   │   ├── image_proc.py               # OpenCV image preprocessing pipeline
│   │   │   ├── llm.py                      # Llama 3 prompt generation & completions
│   │   │   ├── llm_provider.py             # Ollama HTTP client with streaming
│   │   │   ├── ocr.py                      # Tesseract OCR engine & word parser
│   │   │   ├── resource_manager.py         # Dynamic memory monitoring & batching
│   │   │   ├── security.py                 # RBAC enforcement, JWT tokens, hashing
│   │   │   ├── startup_validation.py       # Pre-flight environment & dependency checker
│   │   │   ├── summarization.py            # Recursive document summarizer
│   │   │   ├── text_clean.py               # Regex text sanitization & normalization
│   │   │   ├── vectordb.py                 # ChromaDB collection & search manager
│   │   │   ├── cache/                      # Fingerprinting & duplicate prevention
│   │   │   │   └── fingerprint.py          # SHA-256 caching & duplicate detector
│   │   │   ├── graph/                      # Knowledge Graph implementation
│   │   │   │   ├── manager.py              # Graph manipulation interface
│   │   │   │   ├── reasoning.py            # Graph traversal & relationship inference
│   │   │   │   └── store.py                # SQLite schema for nodes & edges
│   │   │   ├── ingestion/                  # Multi-format ingestion framework
│   │   │   │   ├── detector.py             # MIME/Modality detector
│   │   │   │   ├── engine.py               # Ingestion coordinator
│   │   │   │   ├── table_extractor.py      # Table detection manager
│   │   │   │   └── adapters/               # Specialized file format adapters
│   │   │   │       ├── base.py             # Abstract base adapter
│   │   │   │       ├── manager.py          # Adapter registry & selector
│   │   │   │       ├── csv_adapter.py      # CSV parser
│   │   │   │       ├── docx_adapter.py     # Microsoft Word (.docx) parser
│   │   │   │       ├── image_adapter.py    # Image adapter (.png, .jpg)
│   │   │   │       ├── pdf_adapter.py      # PDF adapter
│   │   │   │       ├── pdf_engines.py      # Abstract PDF extraction interface
│   │   │   │       ├── pymupdf_engine.py   # PyMuPDF implementation
│   │   │   │       ├── pptx_adapter.py     # Microsoft PowerPoint (.pptx) parser
│   │   │   │       ├── table_extractors.py # Table parsing helpers
│   │   │   │       ├── txt_adapter.py      # Plain/Structured text adapter
│   │   │   │       └── xlsx_adapter.py     # Microsoft Excel (.xlsx) parser
│   │   │   ├── model_manager/              # On-demand AI model lifecycle management
│   │   │   │   ├── base_model.py           # Base model wrapper
│   │   │   │   ├── ocr_models.py           # Tesseract & PaddleOCR wrappers
│   │   │   │   └── __init__.py             # ModelManager registry & memory guard
│   │   │   ├── nlp/                        # NLP & Named Entity Recognition
│   │   │   │   ├── base_entity_extractor.py # Base entity interface
│   │   │   │   ├── entity_extractor.py     # Pattern & keyword NER
│   │   │   │   └── advanced_entity_extractor.py # Contextual multi-entity extractor
│   │   │   ├── pipeline/                   # End-to-end processing pipeline
│   │   │   │   ├── classification.py       # Document classification & routing
│   │   │   │   ├── orchestrator.py         # Main processing orchestrator
│   │   │   │   └── quality_check.py        # Image Quality Scoring (IQS)
│   │   │   ├── rag/                        # RAG reasoning & query orchestration
│   │   │   │   ├── agents.py               # Multi-agent routing & synthesis
│   │   │   │   ├── scoring.py              # Hybrid BM25 + Vector scoring
│   │   │   │   └── universal_query.py      # Universal query coordinator
│   │   │   └── vision/                     # Deep vision intelligence layer
│   │   │       ├── interface.py            # Vision engine contract
│   │   │       ├── pipeline.py             # Vision processing orchestrator
│   │   │       ├── result.py               # Standardized vision output models
│   │   │       ├── chart_parser.py         # Chart data & series extractor
│   │   │       ├── diagram_parser.py       # Architecture diagram & flowchart parser
│   │   │       ├── table_parser.py         # Visual table structure parser
│   │   │       └── engines/                # Vision inference backends
│   │   │           ├── base.py             # Abstract vision engine
│   │   │           ├── florence2.py        # Microsoft Florence-2 integration
│   │   │           └── mock.py             # Mock engine for CI / benchmarks
│   │   └── models/                         # Database & Schema representations
│   │       ├── database.py                 # SQLite DatabaseManager & table schemas
│   │       └── schema.py                   # Pydantic schema (CDO, UKS, KO, Edges)
│   ├── scripts/                            # Administrative & benchmarking utilities
│   │   ├── benchmark.py                    # Pipeline benchmarking script
│   │   ├── benchmark_vision.py             # Florence-2 vision benchmark
│   │   ├── create_demo_dataset.py          # Synthetic multimodal demo dataset generator
│   │   ├── download_florence2.py           # Pre-download Florence-2 weights
│   │   ├── generate_benchmark_images.py    # Generates synthetic charts & tables
│   │   ├── generate_docs.py                # Automated documentation generator
│   │   └── seed_users.py                   # Default user & credential seeder
│   └── tests/                              # Unit & integration test suites (24 files)
│
├── data/                                   # Runtime data storage
│   ├── benchmarks/                         # Benchmark charts and test assets
│   ├── ocr_cache/                          # Cached OCR text, JSON bounding boxes, chunks
│   ├── sqlite/                             # Persistent SQLite databases (metadata.db)
│   └── uploads/                            # Stored raw uploaded documents & thumbnails
│
└── frontend/                               # React + Vite Web Client
    ├── index.html                          # HTML entry point
    ├── package.json                        # Frontend NPM dependencies & scripts
    ├── vite.config.js                      # Vite build & proxy configurations
    ├── vitest.config.js                    # Unit test configurations
    ├── src/
    │   ├── App.jsx                         # Main application UI & state container
    │   ├── index.css                       # Design system, themes & component styling
    │   ├── main.jsx                        # React DOM root bootstrapping
    │   ├── setupTests.js                   # Vitest testing setup
    │   ├── components/
    │   │   ├── AuditLogs.jsx               # Security audit trail viewer & exporter
    │   │   ├── ChatSidebar.jsx             # Gemini-style chat session history sidebar
    │   │   └── UserManagement.jsx          # Admin user creation, roles & permissions
    │   ├── context/
    │   │   └── AuthContext.jsx             # React Context for JWT auth & session state
    │   └── pages/
    │       └── Login.jsx                   # Modern secure login authentication page
```

---

## 4. In-Depth File-by-File Technical Breakdown

### 4.1 Root Directory Files

#### [README.md](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/README.md)
- **Purpose:** Primary setup manual and getting-started guide.
- **Key Contents:** Outlines prerequisites (Python 3.10+, Node.js 18+, Tesseract OCR installer, Ollama with `llama3`), instructions for configuring `.env`, backend execution commands (`uvicorn app.main:app`), frontend launch commands (`npm run dev`), and offline operational notes.

#### [benchmark.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/benchmark.py)
- **Purpose:** Standalone system benchmarking script for measuring processing latency and RAM overhead.
- **Key Functionality:** Generates synthetic in-memory document pages, runs them through `PipelineOrchestrator.process_document()`, computes latency and memory deltas with `psutil`, and benchmarks mock vs. real vision pipeline processing.

#### [build_nyayaai_format_paper.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/build_nyayaai_format_paper.py)
- **Purpose:** Compiles and renders the official academic research paper on the Multimodal Offline RAG System into publication-ready IEEE 2-column format.
- **Key Functionality:** Utilizes `python-docx` and `reportlab` to programmatically format typography (Charter/Times), title headers, abstract blocks, methodology tables, architecture figures, and algorithmic formulas, exporting both `Multimodal_Offline_RAG_IEEE_Paper.docx` and `Multimodal_Offline_RAG_IEEE_Paper.pdf`.

#### [extract_fonts.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/extract_fonts.py)
- **Purpose:** Utility script for inspecting font metadata, point sizes, colors, and line coordinates from reference PDF papers using PyMuPDF (`fitz`).

#### [run_custom_tests.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/run_custom_tests.py)
- **Purpose:** Standalone regression script executing DOCX and PPTX adapter test suites without requiring a full pytest runner invocation.

---

### 4.2 Backend: Core Application Entry & Configuration

#### [backend/app/config.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/config.py)
- **Purpose:** Centralized application configuration and runtime directory resolution.
- **Key Parameters:**
  - `BASE_DIR`, `DATA_DIR`, `UPLOADS_DIR`, `PROCESSED_DIR`, `OCR_OUTPUT_DIR`, `SQLITE_DB_PATH`, `CHROMA_DIR`.
  - `TESSERACT_PATH`: Path to the local Tesseract OCR binary.
  - `CHUNK_SIZE` (default 500 tokens), `CHUNK_OVERLAP` (default 50 tokens).
  - Image Quality Thresholds: `IQS_FAST_PATH_THRESHOLD` (0.85), `IQS_ROBUST_PATH_THRESHOLD` (0.50), `BLUR_VARIANCE_THRESHOLD` (100.0), `SNR_THRESHOLD` (1.5).
  - Hardware & Resource Safeguards: `MAX_RAM_USAGE_MB` (12GB), `MAX_CPU_WORKERS` (4), `MAX_VISION_RAM_MB` (4GB).
  - Vision Engine: `VISION_ENABLED`, `VISION_MODEL_PATH` (`microsoft/Florence-2-base`), `VISION_DEVICE` (`auto`).
  - Embedding Model: `BAAI/bge-base-en-v1.5`.

#### [backend/app/main.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/main.py)
- **Purpose:** Main FastAPI application entrypoint.
- **Key Functionality:**
  - Instantiates `FastAPI(title="Multimodal Offline RAG Backend")`.
  - Configures CORS middleware for frontend communication.
  - Implements startup events initializing the SQLite schema (`db_manager._initialize_tables()`) and launching the asynchronous background worker loop (`worker.start()`).
  - Implements shutdown events gracefully terminating background tasks.
  - Registers all API routers: `auth_router`, `upload_router`, `ocr_router`, `rag_router`, `graph_router`, `summarize_router`, `system_router`.
  - Exposes the `/api/health` system health endpoint.

---

### 4.3 Backend: REST API Layer (`backend/app/api/`)

#### [backend/app/api/auth.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/auth.py)
- **Purpose:** User authentication, role assignment, and access token management.
- **Key Endpoints:**
  - `POST /api/auth/login`: Validates credentials against hashed passwords in SQLite, logs audit events, and returns signed JWT bearer tokens containing `user_id`, `username`, and `role`.
  - `GET /api/auth/me`: Validates bearer token and returns current user profile and role privileges.
  - `GET /api/auth/users`: Retrieves all users (restricted to `SYSTEM_ADMIN`).
  - `POST /api/auth/users`: Creates a new user with defined RBAC role (restricted to `SYSTEM_ADMIN`).
  - `DELETE /api/auth/users/{id}`: Deletes user accounts with audit trail (restricted to `SYSTEM_ADMIN`).
  - `PUT /api/auth/users/{id}/role`: Updates user role (restricted to `SYSTEM_ADMIN`).

#### [backend/app/api/upload.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/upload.py)
- **Purpose:** Document upload handling, disk persistence, document lifecycle management, and job polling.
- **Key Endpoints:**
  - `POST /api/upload`: Multi-file upload endpoint. Calculates SHA-256 hashes, saves raw binaries to `data/uploads/`, registers metadata in SQLite with designated security classification (`PUBLIC` to `TOP_SECRET`), and enqueues tasks in `background_jobs`.
  - `GET /api/images`: Lists all registered documents with owner and classification metadata, strictly filtered according to the requesting user's authorization level.
  - `GET /api/images/{id}`: Retrieves specific document metadata.
  - `DELETE /api/images/{id}`: Deletes document, associated files, OCR cache, graph nodes, and vector index entries.
  - `GET /api/images/{id}/thumbnail`: Serves generated image/document preview thumbnails.
  - `GET /api/images/{id}/raw`: Serves original binary document/image stream for download or viewing.
  - `GET /api/jobs/{id}`: Polls processing status of background ingestion jobs (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`).

#### [backend/app/api/ocr.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/ocr.py)
- **Purpose:** OCR processing endpoints, text extraction retrieval, and bounding-box geometry.
- **Key Endpoints:**
  - `POST /api/images/{id}/ocr`: Triggers on-demand background OCR processing for scanned images.
  - `GET /api/images/{id}/ocr/data`: Retrieves complete OCR results including word bounding boxes, lines, confidence scores, and chunk boundaries.
  - `GET /api/images/{id}/ocr/text`: Returns clean, reconstructed full-text transcriptions with automatic fallback extraction for non-image documents.
  - `GET /api/images/{id}/ocr/chunks`: Retrieves segmented semantic chunks.
  - `GET /api/images/{id}/ocr/download/{format}`: Exports extracted text as plain TXT, JSON, or hOCR formats.

#### [backend/app/api/rag.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/rag.py)
- **Purpose:** RAG query engine, semantic vector search, chat session history, and LLM streaming.
- **Key Endpoints:**
  - `POST /api/images/{image_id}/index`: Manually triggers vector embedding generation and ChromaDB insertion for an individual document.
  - `GET /api/search`: Performs hybrid semantic similarity search across indexed document chunks with keyword score boosting, classification filtering, and metadata enrichment.
  - `POST /api/chat`: Universal RAG endpoint. Accepts query, session ID, and optional document attachment IDs; triggers agent routing and graph reasoning; and streams synthesized answer tokens via Server-Sent Events (SSE) alongside grounded citation markers.
  - `GET /api/chat/sessions`: Lists previous chat sessions for the authenticated user.
  - `GET /api/chat/sessions/{id}`: Retrieves conversational turn history for a session.
  - `DELETE /api/chat/sessions/{id}`: Deletes a chat session and associated messages.

#### [backend/app/api/graph.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/graph.py)
- **Purpose:** Knowledge Graph querying, relational traversal, and interactive graph visualization.
- **Key Endpoints:**
  - `GET /api/graph/nodes/{node_id}`: Retrieves knowledge node metadata.
  - `GET /api/graph/nodes/{node_id}/children`: Returns child nodes linked by `CHILD_OF` edges.
  - `GET /api/graph/nodes/{node_id}/parents`: Returns parent nodes.
  - `GET /api/graph/nodes/{node_id}/neighbors`: Multi-hop graph exploration up to 3 hops deep.
  - `GET /api/graph/visualize`: Returns the entire knowledge graph (nodes and directed edges) filtered by the requesting user's classification privileges.

#### [backend/app/api/summarize.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/summarize.py)
- **Purpose:** Hierarchical document summarization endpoint.
- **Key Endpoints:**
  - `POST /api/documents/{document_id}/summarize`: Validates user permissions, invokes `DocumentSummarizer`, caches the summary in the database, and records an audit log event.

#### [backend/app/api/system.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/api/system.py)
- **Purpose:** System metrics aggregation and administrative audit viewing.
- **Key Endpoints:**
  - `GET /api/system/dashboard`: Aggregates total document counts, background job queue states, knowledge graph nodes and edges, user accounts, and hardware status for the admin dashboard.
  - `GET /api/system/audit`: Retrieves recent structured audit logs (restricted to `SYSTEM_ADMIN`).

---

### 4.4 Backend: Core Ingestion Framework (`backend/app/core/ingestion/`)

#### [backend/app/core/ingestion/engine.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/engine.py)
- **Purpose:** Coordinates format detection and selects the appropriate file adapter.
- **Key Functionality:** Implements `IngestionEngine.process_file(file_path)` which calls `ModalityDetector`, retrieves the registered adapter from `AdapterManager`, and converts the raw file into a normalized `CommonDocumentObject` (CDO).

#### [backend/app/core/ingestion/detector.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/detector.py)
- **Purpose:** Robust file format and modality detection using file signatures (magic bytes) and file extensions.
- **Supported Modalities:** `pdf`, `docx`, `pptx`, `xlsx`, `csv`, `txt`, and `image` (`png`, `jpg`, `jpeg`, `tiff`, `bmp`).

#### [backend/app/core/ingestion/table_extractor.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/table_extractor.py)
- **Purpose:** High-level coordinator for extracting tabular data structures from documents and converting them into Markdown, HTML, and JSON representations.

#### [backend/app/core/ingestion/adapters/base.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/base.py)
- **Purpose:** Defines the abstract base class `BaseAdapter` with the interface method `extract(file_path: Path) -> CommonDocumentObject`.

#### [backend/app/core/ingestion/adapters/manager.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/manager.py)
- **Purpose:** Adapter registry singleton mapping modality identifiers to adapter classes (`ImageAdapter`, `PDFAdapter`, `DocxAdapter`, `PptxAdapter`, `XlsxAdapter`, `CsvAdapter`, `TxtAdapter`).

#### [backend/app/core/ingestion/adapters/pdf_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/pdf_adapter.py) & [pymupdf_engine.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/pymupdf_engine.py)
- **Purpose:** High-performance PDF ingestion.
- **Key Functionality:** Uses PyMuPDF (`fitz`) to extract selectable text blocks, page geometries, embedded vector drawings, and rasterized page images for OCR fallback when digital text is absent.

#### [backend/app/core/ingestion/adapters/docx_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/docx_adapter.py)
- **Purpose:** Microsoft Word (.docx) document ingestion.
- **Key Functionality:** Traverses XML structure using `python-docx`. Extracts styled headings (Heading 1-6), body paragraphs, bulleted lists, running headers and footers, embedded tables with column spans, and embedded media assets.

#### [backend/app/core/ingestion/adapters/pptx_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/pptx_adapter.py)
- **Purpose:** Microsoft PowerPoint (.pptx) presentation ingestion.
- **Key Functionality:** Iterates over presentation slides using `python-pptx`. Extracts slide titles, text boxes, speaker notes, slide tables, and embedded chart objects.

#### [backend/app/core/ingestion/adapters/xlsx_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/xlsx_adapter.py)
- **Purpose:** Microsoft Excel (.xlsx) workbook ingestion.
- **Key Functionality:** Uses `openpyxl` in read-only data mode. Extracts all sheets, detects table boundaries, parses row/column headers, and formats tabular data into clean Markdown tables.

#### [backend/app/core/ingestion/adapters/csv_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/csv_adapter.py)
- **Purpose:** Comma-Separated Values (CSV) ingestion.
- **Key Functionality:** Detects delimiter encodings, parses rows and columns, and generates structured table objects and textual summaries for vector indexing.

#### [backend/app/core/ingestion/adapters/txt_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/txt_adapter.py)
- **Purpose:** Plain text and structured text (.txt, .md, .log) ingestion.
- **Key Functionality:** Detects character encoding (UTF-8, Latin-1), identifies Markdown/heading hierarchies, and structures text into paragraphs and sections.

#### [backend/app/core/ingestion/adapters/image_adapter.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ingestion/adapters/image_adapter.py)
- **Purpose:** Standalone image (.png, .jpg, .jpeg) ingestion.
- **Key Functionality:** Loads image data into OpenCV BGR numpy arrays, computes SHA-256 fingerprint, and initializes the CDO for the Vision and OCR pipelines.

---

### 4.5 Backend: Deep Vision Intelligence (`backend/app/core/vision/`)

#### [backend/app/core/vision/pipeline.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vision/pipeline.py)
- **Purpose:** Orchestrator for deep visual comprehension of images, charts, and diagrams.
- **Key Functionality:** Coordinates Microsoft Florence-2 model tasks (`<MORE_DETAILED_CAPTION>`, `<OCR_WITH_REGION>`, `<DENSE_REGION_CAPTION>`), delegates visual elements to specialized parsers, and produces rich semantic knowledge blocks.

#### [backend/app/core/vision/engines/florence2.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vision/engines/florence2.py)
- **Purpose:** Direct integration wrapper for Microsoft Florence-2 Vision-Language Model.
- **Key Functionality:** Loads model and processor weights locally with PyTorch, executes GPU/CPU inference, parses task tokens, and formats bounding box coordinates and captions.

#### [backend/app/core/vision/chart_parser.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vision/chart_parser.py)
- **Purpose:** Extracts data points, axes, legends, and trend descriptions from bar charts, line graphs, and pie charts.

#### [backend/app/core/vision/diagram_parser.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vision/diagram_parser.py)
- **Purpose:** Parses system architecture diagrams, network topologies, and flowcharts into connected nodes and directed relationship edges.

#### [backend/app/core/vision/table_parser.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vision/table_parser.py)
- **Purpose:** Converts visual table bounding boxes into structured rows and cells.

#### [backend/app/core/vision/engines/mock.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vision/engines/mock.py)
- **Purpose:** Fast mock engine providing deterministic vision outputs for automated testing and CPU benchmarking.

---

### 4.6 Backend: Processing Pipeline & Quality Control (`backend/app/core/pipeline/`)

#### [backend/app/core/pipeline/orchestrator.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/pipeline/orchestrator.py)
- **Purpose:** The central pipeline controller uniting all ingestion, quality analysis, OCR, vision, schema construction, and graph building stages.
- **Processing Flow:**
  1. Checks Level-1 fingerprint cache for duplicate detection.
  2. Runs `ImageQualityAnalyzer` to obtain Image Quality Score (IQS).
  3. Classifies document type via `DocumentClassifier` to determine optimal processing profile.
  4. Preprocesses images using OpenCV (CLAHE, deskewing, binarization).
  5. Runs OCR (Tesseract) and Vision Pipeline (Florence-2).
  6. Constructs `UniversalKnowledgeSchema` with `KnowledgeObject` nodes and `RelationshipEdge` links.
  7. Passes schema to `SemanticChunker` to prepare text chunks.
  8. Generates embeddings via `LocalEmbeddingsCalculator` and indexes them in `VectorDatabaseManager`.
  9. Persists graph nodes and edges to SQLite via `GraphManager`.

#### [backend/app/core/pipeline/quality_check.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/pipeline/quality_check.py)
- **Purpose:** Computes objective image quality metrics to route documents intelligently.
- **Key Metrics:**
  - Blur score (Laplacian variance).
  - Contrast score (Michelson / RMS contrast).
  - Signal-to-Noise Ratio (SNR).
  - Resolution and DPI assessment.
  - Image Quality Score (IQS): Weighted composite score (0.0 to 1.0) determining whether a document follows the Fast Path, Robust Path, or Heavy Enhancement Path.

#### [backend/app/core/pipeline/classification.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/pipeline/classification.py)
- **Purpose:** Analyzes visual layout and extracted features to classify documents into categories (Form, Technical Report, Invoice, Presentation, Architecture Diagram) and select appropriate downstream processing profiles.

---

### 4.7 Backend: RAG, Retrieval, and Reasoning (`backend/app/core/rag/`)

#### [backend/app/core/rag/universal_query.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/rag/universal_query.py)
- **Purpose:** The central RAG query coordinator.
- **Key Functionality:**
  - Integrates user queries with multi-session chat history.
  - Directs query execution through `MultiAgentSystem`.
  - Performs hybrid dense vector search and keyword matching.
  - Injects top matching chunks (capped at 10 chunks to prevent context overflow) into the local LLM prompt.
  - Supports both synchronous synthesis and real-time Server-Sent Event (SSE) token streaming.

#### [backend/app/core/rag/agents.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/rag/agents.py)
- **Purpose:** Specialized multi-agent system for complex reasoning:
  - `RoutingAgent`: Analyzes query intent (factual lookup, visual analysis, relationship traversal, summarization).
  - `DocumentAgent`: Focuses on textual paragraph and table retrieval.
  - `VisionAgent`: Queries visual assets, charts, diagrams, and Florence-2 captions.
  - `SynthesisAgent`: Combines multimodal context into a cohesive response with citations.

#### [backend/app/core/rag/scoring.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/rag/scoring.py)
- **Purpose:** Hybrid retrieval reranking.
- **Scoring Formula:** Blends dense vector cosine similarity with BM25 keyword matching, confidence scores, and proximity boosts to rank the most pertinent document chunks first.

---

### 4.8 Backend: Core Services & Infrastructure

#### [backend/app/core/background_worker.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/background_worker.py)
- **Purpose:** Robust SQLite-backed task queue processor (`HardenedBackgroundWorker`).
- **Features:** Concurrency control via `asyncio.Semaphore`, retry mechanisms with exponential backoff, crash recovery for stale jobs stuck in `PROCESSING`, and non-blocking asynchronous execution.

#### [backend/app/core/resource_manager.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/resource_manager.py)
- **Purpose:** Hardware resource monitor preventing memory exhaustion.
- **Features:** Queries CPU and RAM via `psutil`. Decides whether documents should be processed in-memory or streamed to temporary cache on disk, and dynamically adjusts batch processing sizes.

#### [backend/app/core/embeddings.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/embeddings.py)
- **Purpose:** Offline vector embeddings generator using SentenceTransformers (`BAAI/bge-base-en-v1.5`). Generates 768-dimensional normalized dense vectors.

#### [backend/app/core/vectordb.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/vectordb.py)
- **Purpose:** Wrapper around ChromaDB and SQLite vector storage. Manages collection creation, vector insertion, metadata filtering, and distance-based similarity queries.

#### [backend/app/core/llm_provider.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/llm_provider.py) & [llm.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/llm.py)
- **Purpose:** Interface to the local Ollama LLM service running `llama3`.
- **Key Features:** Sets an 8192-token context window, handles HTTP connections with a 300-second timeout to support slow CPU environments, formats system prompts, and yields tokens asynchronously for streaming output.

#### [backend/app/core/ocr.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/ocr.py)
- **Purpose:** Tesseract OCR wrapper.
- **Key Features:** Runs Tesseract subprocess, parses TSV and hOCR outputs, extracts word coordinates and bounding boxes, groups words into lines and paragraphs, and computes line-level confidence scores.

#### [backend/app/core/image_proc.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/image_proc.py)
- **Purpose:** OpenCV image preprocessing pipeline.
- **Key Operations:** Grayscale conversion, Contrast Limited Adaptive Histogram Equalization (CLAHE), Otsu adaptive binarization, Hough transform deskewing, and bilateral filtering for noise reduction.

#### [backend/app/core/chunking.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/chunking.py)
- **Purpose:** Semantic chunking engine (`SemanticChunker`). Segments text blocks while respecting paragraph and heading boundaries, preserving metadata (document ID, page number, bounding boxes, classification).

#### [backend/app/core/security.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/security.py)
- **Purpose:** Security and RBAC enforcement.
- **Key Components:**
  - Password hashing using bcrypt.
  - JWT token generation and decoding (`PyJWT`).
  - `Role` enum (`SYSTEM_ADMIN`, `INTELLIGENCE_ANALYST`, `DOCUMENT_OFFICER`, `AUDITOR`, `STANDARD_USER`).
  - Classification hierarchy (`PUBLIC` < `INTERNAL` < `CONFIDENTIAL` < `SECRET` < `TOP_SECRET`).
  - `require_roles()` and `authorize_document_classification()` FastAPI dependencies.

#### [backend/app/core/audit.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/audit.py)
- **Purpose:** Security and audit event logger (`AuditLogger`). Records immutable audit entries (timestamp, user, action, resource ID, IP address, status) into the SQLite `audit_logs` table.

#### [backend/app/core/summarization.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/summarization.py)
- **Purpose:** Document summarization service (`DocumentSummarizer`). Generates structured executive summaries using map-reduce style local LLM prompts.

#### [backend/app/core/events.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/events.py)
- **Purpose:** Lightweight in-memory event bus (`event_bus`) implementing publish/subscribe hooks for pipeline telemetry (`PipelineStarted`, `QualityReportGenerated`, `PipelineCompleted`).

#### [backend/app/core/cache/fingerprint.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/cache/fingerprint.py)
- **Purpose:** Level-1 caching and duplicate prevention. Calculates and matches SHA-256 hashes against previous schemas to prevent redundant processing.

#### [backend/app/core/graph/manager.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/graph/manager.py), [reasoning.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/graph/reasoning.py), & [store.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/graph/store.py)
- **Purpose:** SQLite-backed Knowledge Graph store and multi-hop reasoning algorithms for traversing complex relationships across documents.

#### [backend/app/core/nlp/](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/nlp/)
- **Purpose:** Named Entity Recognition (`EntityExtractor`, `AdvancedEntityExtractor`). Extracts and categorizes organizations, geopolitical entities, equipment identifiers, dates, and classification markers.

#### [backend/app/core/model_manager/](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/core/model_manager/)
- **Purpose:** AI Model Lifecycle Manager. Coordinates lazy loading and memory release of heavy AI models (Tesseract, PaddleOCR, Florence-2) to adhere to hardware RAM limits.

#### [backend/app/models/database.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/models/database.py)
- **Purpose:** SQLite database manager and schema definition.
- **Tables Managed:**
  1. `documents`: Document ID, SHA-256 hash, filename, MIME type, modality, status, owner ID, security classification, serialized schema JSON.
  2. `background_jobs`: Task queue tracking job state, retry count, timestamps, error logs.
  3. `users`: User credentials, bcrypt password hashes, and assigned RBAC roles.
  4. `audit_logs`: Tamper-evident record of all system events, queries, logins, and downloads.
  5. `knowledge_objects`: Graph node records representing semantic blocks, tables, pages, and figures.
  6. `relationship_edges`: Directed edges representing relationships (`CHILD_OF`, `REFERENCES`, `CONNECTED_TO`).
  7. `chat_sessions`: User conversation session records.
  8. `chat_messages`: Turn-by-turn chat history linking user questions, AI responses, and citations.
  9. `processing_history`: Processing stage benchmarks and latency metrics.

#### [backend/app/models/schema.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/app/models/schema.py)
- **Purpose:** Formal Pydantic schemas defining the standard data contracts:
  - `CommonDocumentObject` (CDO): Input contract produced by adapters.
  - `KnowledgeObject` (KO): Atomic semantic block with content, bounding box, engine used, and confidence.
  - `RelationshipEdge`: Graph link connecting two Knowledge Objects.
  - `UniversalKnowledgeSchema` (UKS): Output contract representing fully processed documents.

---

### 4.9 Backend: Utility & Maintenance Scripts (`backend/scripts/`)

- [benchmark.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/benchmark.py): Measures document processing speed, latency, and peak RAM consumption.
- [benchmark_vision.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/benchmark_vision.py): Benchmarks Florence-2 vision model inference across charts and tables.
- [create_demo_dataset.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/create_demo_dataset.py): Generates sample multi-format documents (`National_Surveillance_Architecture.pdf`, `Network_Architecture.pptx`, `System_Deployment_Specifications.docx`, etc.).
- [download_florence2.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/download_florence2.py): Pre-downloads Hugging Face model weights for Microsoft Florence-2 to enable offline deployment.
- [generate_benchmark_images.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/generate_benchmark_images.py): Synthesizes test charts and diagrams using Matplotlib and OpenCV.
- [generate_docs.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/generate_docs.py): Generates automated technical documentation.
- [seed_users.py](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/backend/scripts/seed_users.py): Seeds initial default user accounts (`admin`, `analyst`, `auditor`, `user`) with hashed passwords.

---

### 4.10 Backend: Test Suites (`backend/tests/`)

The repository includes 24 comprehensive test suites covering all layers of the architecture:
- `conftest.py`: Shared pytest fixtures, temporary database connections, and mock authentication tokens.
- `test_api.py`: Tests core REST endpoints, uploads, status polling, and health checks.
- `test_auth.py`: Tests JWT generation, authentication failure handling, and RBAC privilege enforcement.
- `test_chat_memory.py`: Verifies multi-turn chat session storage, session recall, and message deletion.
- `test_csv_adapter.py`, `test_docx_adapter.py`, `test_pptx_adapter.py`, `test_pdf_adapter.py`, `test_xlsx_adapter.py`, `test_txt_adapter.py`: Modality-specific adapter tests verifying accurate text extraction, tables, and error handling for corrupted files.
- `test_vision_pipeline.py`: Tests the Florence-2 vision intelligence pipeline and parser components.
- `test_pipeline.py` & `test_pipeline_relationships.py`: Validates end-to-end processing and graph edge generation.
- `test_universal_multimodal_query.py`: Tests multi-agent routing, hybrid scoring, and citation generation.
- `test_scoring.py`: Validates BM25 and vector score fusion algorithms.
- `test_step1_abstractions.py` through `test_step5_multi_agent.py`: Stepwise verification tests corresponding to project development milestones.

---

### 4.11 Frontend: User Interface & Client Architecture (`frontend/src/`)

#### [frontend/src/main.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/main.jsx)
- **Purpose:** React application bootstrap. Renders `<App />` wrapped in `<AuthProvider>` into the root DOM container.

#### [frontend/src/index.css](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/index.css)
- **Purpose:** Complete custom design system and stylesheet.
- **Key Styling Features:** Dark-mode color palette, CSS variables (`--bg-primary`, `--accent-blue`, `--border-color`), glassmorphism cards, responsive layouts, chat bubble formatting, and OCR overlay bounding-box styling.

#### [frontend/src/context/AuthContext.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/context/AuthContext.jsx)
- **Purpose:** Global authentication and session state provider.
- **Key Features:** Stores JWT token in `localStorage`, verifies token validity against `/api/auth/me`, handles login/logout actions, and exposes `user`, `token`, `login`, and `logout` to all components.

#### [frontend/src/pages/Login.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/pages/Login.jsx)
- **Purpose:** Secure authentication screen.
- **Key Features:** Professional dark-mode interface with username/password inputs, role preview cards, loading spinners, and error message handling.

#### [frontend/src/components/ChatSidebar.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/components/ChatSidebar.jsx)
- **Purpose:** Gemini/ChatGPT-style collapsible sidebar for managing conversation history.
- **Key Features:** Fetches user chat sessions from `/api/chat/sessions`, allows initiating a new chat session, switching between active sessions, and deleting conversation threads.

#### [frontend/src/components/UserManagement.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/components/UserManagement.jsx)
- **Purpose:** Administrative user management panel for `SYSTEM_ADMIN` users.
- **Key Features:** Lists user accounts, provides a form to create users with defined RBAC roles (`SYSTEM_ADMIN`, `INTELLIGENCE_ANALYST`, `DOCUMENT_OFFICER`, `AUDITOR`, `STANDARD_USER`), and allows deleting accounts.

#### [frontend/src/components/AuditLogs.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/components/AuditLogs.jsx)
- **Purpose:** Security audit log inspection panel for compliance monitoring.
- **Key Features:** Displays structured audit logs (event types, usernames, roles, actions, timestamps, statuses, and IP addresses) with text-based search filtering and JSON export capability.

#### [frontend/src/App.jsx](file:///c:/Users/jaga2/Downloads/Multimodal%20RAG%20System/frontend/src/App.jsx)
- **Purpose:** Primary application shell containing layout navigation and interactive workspace views:
  1. **Dashboard Tab:** Displays system metrics (total documents, background job queue distribution, knowledge graph node/edge counts, active users) and system health indicators.
  2. **Upload Tab:** Interactive drag-and-drop file uploader with classification selector (`PUBLIC` to `TOP_SECRET`), upload progress indicator, and batch processing status tracking.
  3. **Gallery Tab:** Responsive grid displaying processed document cards with modality icons, classification badges, and status tags. Supports document deletion, triggering OCR, and opening the inspection modal.
  4. **Document Inspection Modal:** Comprehensive viewer featuring side-by-side original file view (via `@cyntler/react-doc-viewer`) and OCR bounding-box overlay, tabbed switching between reconstructed full-text, segmented semantic chunks, tabular views, and Florence-2 visual descriptions.
  5. **Chat Tab (Gemini-Styled Interface):**
     - Left sidebar for multi-session conversation history.
     - Conversational chat thread supporting document attachments.
     - Real-time token-by-token streaming of responses from local Llama 3 via Server-Sent Events (SSE).
     - Grounded source citations displaying document titles, page numbers, confidence ratings, and bounding-box coordinates with click-to-preview functionality.
     - Sub-tab for **Semantic Search**, enabling standalone similarity queries with keyword score breakdowns.
  6. **Users Tab:** Hosts `<UserManagement />` for system administrators.
  7. **Audit Tab:** Hosts `<AuditLogs />` for security officers and administrators.
  8. **Settings Tab:** Displays active pipeline thresholds, hardware limits, and offline model statuses.

---

## 5. Security Architecture & RBAC Matrix

| Role | Permitted Classifications | Allowed Operations |
| :--- | :--- | :--- |
| **SYSTEM_ADMIN** | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `SECRET`, `TOP_SECRET` | Full system control: Upload, Delete, Index, View Audit Logs, Manage Users, View Dashboard. |
| **INTELLIGENCE_ANALYST** | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `SECRET`, `TOP_SECRET` | Document Upload, Semantic Search, Chat, Summarize, Graph Visualization, View Dashboard. |
| **DOCUMENT_OFFICER** | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL` | Document Upload, Document Deletion, Re-trigger OCR and Vector Indexing. |
| **AUDITOR** | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL` | Read-only inspection of document registry, metadata, and compliance Audit Logs. |
| **STANDARD_USER** | `PUBLIC`, `INTERNAL` | Basic Semantic Search and Chat over authorized public and internal documents. |

---

## 6. End-to-End Execution Flow

```
1. Upload & Ingestion:
   User Uploads File -> Upload Router computes SHA-256 -> File saved to data/uploads/
   -> Metadata saved to SQLite -> Background Job queued

2. Background Worker Processing:
   HardenedBackgroundWorker picks up job -> IngestionEngine detects modality
   -> Format Adapter (PDF/DOCX/PPTX/etc.) extracts text, tables, images
   -> Returns CommonDocumentObject (CDO)

3. Pipeline Orchestration & Enrichment:
   PipelineOrchestrator receives CDO -> Checks Level-1 fingerprint cache
   -> ImageQualityAnalyzer scores image quality (IQS)
   -> OpenCV executes binarization, deskewing, CLAHE
   -> Tesseract extracts text & bounding boxes; Florence-2 generates captions & vision blocks
   -> UniversalKnowledgeSchema (UKS) created with KnowledgeObjects and RelationshipEdges
   -> Knowledge Graph updated in SQLite

4. Chunking & Vector Indexing:
   SemanticChunker divides text/schema into overlapping chunks with metadata
   -> LocalEmbeddingsCalculator creates 768-dim dense embeddings (BGE-base)
   -> Chunks and vectors indexed in ChromaDB vector store
   -> Job marked COMPLETED in SQLite

5. Retrieval & Universal Query (Chat):
   User submits question in Chat UI -> UniversalQueryEngine checks chat session
   -> MultiAgentSystem routes query -> Hybrid scoring matches ChromaDB chunks
   -> Top relevant chunks and graph context assembled into Llama 3 prompt
   -> Ollama generates response -> Tokens streamed in real-time to Frontend via SSE
   -> Citations with bounding boxes displayed alongside response
```

---

*This guide provides complete structural and operational coverage of every file and subsystem in the Multimodal Offline RAG System.*
