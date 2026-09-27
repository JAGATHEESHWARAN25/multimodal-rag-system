# Multimodal Offline RAG System

A 100% air-gapped, production-grade **Multimodal Retrieval-Augmented Generation (RAG) System** engineered for secure, local desktop CPU execution without external cloud API dependencies or network exfiltration risks.

The system natively ingests **7 document and visual modalities**—PDF, DOCX, PPTX, PNG/JPG Images, TXT, CSV, and XLSX—into unified Knowledge Objects, featuring dual-layer vector/graph storage, pre-LLM Role-Based Access Control (RBAC) security boundaries, a 6-stage RAG orchestration pipeline, and deterministic citation overlays.

---

## 🌟 Key System Features

- **100% Air-Gapped Local Execution**: Zero outbound network traffic or external cloud model dependencies.
- **Native 7-Modality Ingestion**: Custom open-source adapters for PDF (`PyMuPDF`), DOCX (`python-docx`), PPTX (`python-pptx`), XLSX/CSV (`openpyxl`/`csv.Sniffer`), Images (`PaddleOCR`/`EasyOCR`), and TXT.
- **Local Computer Vision & OCR**: Local PaddleOCR and EasyOCR engines extract dense visual text blocks and compute normalized bounding box coordinates (`[ymin, xmin, ymax, xmax]`).
- **Dual-Layer Hybrid Storage**:
  - **ChromaDB**: 384-dimensional dense vector embeddings (`All-MiniLM-L6-v2`) for semantic search.
  - **SQLite Knowledge Graph**: Relational schema capturing `CHILD_OF`, `MENTIONS`, and `NEXT_CELL` entity edges with Breadth-First Search (BFS) pathfinding.
- **Pre-LLM RBAC Security Boundary**: Evaluates user clearance ranks (`PUBLIC` -> `INTERNAL` -> `CONFIDENTIAL` -> `SECRET`) prior to prompt compilation, preventing unauthorized passage exposure.
- **6-Stage RAG Orchestration**: Autonomous agent pipeline comprising `QueryPlanner`, `RetrievalAgent`, `GraphAgent`, `EvidenceAgent`, `AnswerAgent`, and `CitationAgent`.
- **Deterministic Citation Attribution**: Binds answers to exact page numbers, spreadsheet cell coordinates (e.g., `Sheet1!B12`), and visual bounding box overlays.
- **Essentialist Light UI**: Responsive React 18 / Vite workspace supporting interactive chat SSE streaming, knowledge graph visualization, multi-document comparison, and security audit logging.

---

## 🛠 Prerequisites

Before starting, ensure you have the following installed on your local workstation:

1. **Python 3.10+** (Added to system PATH)
2. **Node.js (v18+) & npm**
3. **Ollama**:
   - Download and install [Ollama](https://ollama.com/)
   - Open a terminal and run `ollama run llama3` to download the quantized Llama 3 8B model locally.

---

## 🚀 Step-by-Step Setup

### 1. Backend Setup

Open a terminal in the root directory and navigate to the backend folder:

```bash
cd backend
```

Create a Python virtual environment and activate it:

```bash
# On Windows PowerShell / Command Prompt:
python -m venv venv
venv\Scripts\activate

# On Linux / macOS:
# source venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
ENVIRONMENT=development
LOG_LEVEL=INFO
CHUNK_SIZE=500
CHUNK_OVERLAP=50
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Start the FastAPI backend server:

```bash
python -m uvicorn app.main:app --port 8000 --reload
```

The backend API will be live at `http://localhost:8000` (Swagger UI at `http://localhost:8000/docs`).

---

### 2. Frontend Setup

Open a **new** terminal window in the root directory and navigate to the frontend folder:

```bash
cd frontend
```

Install Node modules:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open `http://localhost:5173` in your web browser to access the Document Intelligence Workspace.

---

## 🧪 Running Automated Test Suites

### Backend Pytest Integration Suite (91 Tests)

```bash
cd backend
pytest
```

### Frontend Vitest UI Suite (28 Tests)

```bash
cd frontend
npm run test
```

---

## 📖 Usage & Workflow

1. **Login & Session Authorization**: Log in with security clearance credentials (`ADMIN`, `OFFICER`, `VIEWER`).
2. **Multi-Format Document Ingestion**: Upload PDF, DOCX, PPTX, PNG/JPG, TXT, CSV, or XLSX files in the Gallery workspace.
3. **Automatic Hybrid Indexing**: Files are fingerprinted via SHA-256 duplicate detection, parsed into Knowledge Objects, embedded in ChromaDB, and linked in the SQLite Knowledge Graph.
4. **Interactive Chat Query**: Ask complex natural language questions. The 6-agent RAG pipeline plans retrieval, traverses graph nodes, filters passages via pre-LLM RBAC rules, streams Ollama tokens via SSE, and highlights bounding box citations.
5. **Knowledge Graph & Multi-Doc Analysis**: Explore entity relationship graphs, perform side-by-side document comparisons, and inspect security audit logs.
