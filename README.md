# Multimodal RAG System (NTRO)

This is a local, secure AI assistant that uses Retrieval-Augmented Generation (RAG) to search and chat with your processed documents and images. It features a FastAPI backend and a React/Vite frontend.

## Prerequisites

Before starting, ensure you have the following installed on your system:
1. **Python 3.10+** (Ensure it is added to your system PATH)
2. **Node.js (v18+)**
3. **Tesseract OCR**: 
   - Download the Windows installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install it (usually to `C:\Program Files\Tesseract-OCR`)
4. **Ollama**:
   - Download and install [Ollama](https://ollama.com/)
   - Open your terminal and run `ollama run llama3` to download the Llama 3 model (this is required for the local LLM).

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

Install the backend dependencies:
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
```

Start the backend FastAPI server:
```bash
python -m uvicorn app.main:app --port 8000 --reload
```
The backend API will be available at http://localhost:8000.

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

## Usage

1. Open the web interface.
2. Navigate to the **Gallery** to upload documents or screenshots.
3. The backend will automatically process the images using OCR, create semantic embeddings, and store them locally in ChromaDB and SQLite.
4. Go to the **Chat** interface to query your documents, or use the **Semantic Search** tab to perform keyword-boosted similarity searches.

*Note: All data stays on your local machine and operates entirely offline.*
