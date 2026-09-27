# Multimodal RAG System (NTRO)

This is a local, secure AI assistant that uses Retrieval-Augmented Generation (RAG) to search and chat with your processed documents, spreadsheets, slides, and images. It features a FastAPI backend and a React/Vite frontend operating 100% offline.

---

## 🌟 Key Features

- **Native 7-Modality Ingestion**: Natively processes PDF, DOCX, PPTX, PNG/JPG Images, TXT, CSV, and XLSX formats preserving table structures, cell coordinates (`Sheet1!B12`), and slide hierarchies.
- **Local OCR & Computer Vision**: Integrated local PaddleOCR and EasyOCR engines extract text lines and normalized bounding box coordinates (`[ymin, xmin, ymax, xmax]`).
- **Dual Vector-Graph Hybrid Storage**:
  - **ChromaDB**: 384-dimensional dense vector embeddings (`all-MiniLM-L6-v2`) for semantic search.
  - **SQLite Knowledge Graph**: Relational schema capturing `CHILD_OF`, `MENTIONS`, and `NEXT_CELL` entity edges with Breadth-First Search (BFS) pathfinding.
- **Pre-LLM RBAC Security Filter**: Hierarchical authorization checking user clearance ranks (`PUBLIC` -> `INTERNAL` -> `CONFIDENTIAL` -> `SECRET`) prior to prompt compilation.
- **6-Stage RAG Orchestrator**: Autonomous agent pipeline comprising `QueryPlanner`, `RetrievalAgent`, `GraphAgent`, `EvidenceAgent`, `AnswerAgent`, and `CitationAgent`.
- **Auditable Citation Attribution**: Deterministic answer grounding with exact page numbers, spreadsheet cell ranges, and visual bounding box overlays.
- **Rich Interactive UI**: Responsive Essentialist Light theme supporting multi-file chat SSE streaming, Knowledge Graph visualization, multi-doc comparison, security audit logs, and PDF citation report generation.

---

## Prerequisites

Before starting, ensure you have the following installed on your system:
1. **Python 3.10+** (Ensure it is added to your system PATH)
2. **Node.js (v18+)**
3. **Tesseract OCR / PaddleOCR**: 
   - Download the Windows installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install it (usually to `C:\Program Files\Tesseract-OCR`)
4. **Ollama**:
   - Download and install [Ollama](https://ollama.com/)
   - Open your terminal and run `ollama run llama3` to download the quantized Llama 3 8B model (required for local LLM inference).

---

## Step-by-Step Setup

### 1. Backend Setup

Open a terminal or command prompt in the **root directory** of this project, then navigate to the backend:

```bash
cd backend
```

Create a Python virtual environment and activate it:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate
```

Install the backend dependencies (includes PyMuPDF, python-docx, python-pptx, openpyxl, PaddleOCR, EasyOCR, ChromaDB, SQLAlchemy):
```bash
pip install -r requirements.txt
```

Create a `.env` file in the `backend` folder to configure your local paths. You can create a file named `.env` and add the following lines (update `TESSERACT_PATH` if you installed it somewhere else):

```env
ENVIRONMENT=development
LOG_LEVEL=INFO
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
CHUNK_SIZE=500
CHUNK_OVERLAP=50
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Start the backend FastAPI server:
```bash
python -m uvicorn app.main:app --port 8000 --reload
```
The backend API will be available at http://localhost:8000 (Interactive API Docs at http://localhost:8000/docs).

---

### 2. Frontend Setup

Open a **new** terminal window in the root directory, then navigate to the frontend:

```bash
cd frontend
```

Install the Node modules:
```bash
npm install
```

Start the Vite development server:
```bash
npm run dev
```

The frontend will start (usually on http://localhost:5173). Open that URL in your browser to access the Document Intelligence Workspace.

---

## 🧪 Running Automated Tests

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

## Usage

1. Open the web interface at `http://localhost:5173`.
2. Authenticate with security clearance credentials (`ADMIN`, `OFFICER`, `VIEWER`).
3. Navigate to the **Gallery / Document Upload** workspace to upload multi-format files (PDF, DOCX, PPTX, PNG/JPG, TXT, CSV, XLSX).
4. The backend automatically processes files using local OCR, builds ChromaDB vector embeddings, and constructs the SQLite Knowledge Graph.
5. Go to the **Chat** interface to submit natural language queries. The 6-agent RAG pipeline retrieves relevant chunks, verifies pre-LLM RBAC clearance, streams Llama 3 SSE tokens, and displays bounding box citation highlights.
6. Explore **Knowledge Graph**, **Document Comparison**, and **Audit Logs** tabs for deep intelligence analysis.

*Note: All data stays on your local machine and operates 100% offline.*
