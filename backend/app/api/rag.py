import logging
from fastapi import APIRouter, HTTPException, status, Query
from app.config import OCR_OUTPUT_DIR
from app.models.database import DatabaseManager
from app.core.embeddings import LocalEmbeddingsCalculator
from app.core.vectordb import VectorDatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["RAG & Semantic Search"])

@router.post("/images/{image_id}/index", status_code=status.HTTP_200_OK)
def index_document(image_id: str):
    """Manually triggers vector embedding generation and ChromaDB indexing for a document."""
    record = DatabaseManager.get_image(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document record not found in SQLite metadata registry."
        )

    # Ensure document OCR has been completed successfully
    if record["status"] != "Completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document OCR is not complete. Please process OCR before vector indexing."
        )

    chunks_path = OCR_OUTPUT_DIR / f"{image_id}_chunks.json"
    if not chunks_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document chunks file missing. Please regenerate OCR."
        )

    try:
        import json
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not chunks:
            return {
                "id": image_id,
                "status": "Skipped",
                "message": "Document contains no text chunks. Seeding skipped.",
                "chunks_count": 0
            }

        # Calculate vector representations and insert to index
        logger.info(f"Manually indexing document chunks for {image_id}...")
        texts = [chunk["text"] for chunk in chunks]
        embeddings = LocalEmbeddingsCalculator.calculate_embeddings(texts)
        VectorDatabaseManager.index_document_chunks("document_chunks", chunks, embeddings)
        
        return {
            "id": image_id,
            "status": "Indexed",
            "chunks_count": len(chunks)
        }
    except Exception as e:
        logger.error(f"Manual index compilation failed for {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile vector index: {str(e)}"
        )

@router.get("/images/search")
def semantic_search(
    query: str = Query(..., description="The search phrase to query against documents"),
    limit: int = Query(5, description="Maximum number of relevant results to return")
):
    """Executes a local semantic vector search against all indexed document text chunks."""
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query parameter cannot be empty."
        )

    try:
        # Calculate search query vector embedding
        query_vector = LocalEmbeddingsCalculator.calculate_query_embedding(query)
        
        # Execute query search in local vector index
        matches = VectorDatabaseManager.semantic_query("document_chunks", query_vector, query, limit)
        
        return matches
    except Exception as e:
        logger.error(f"Semantic vector search failed for query '{query}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Semantic search index is currently unavailable."
        )

from pydantic import BaseModel
from typing import List

class ChatMessage(BaseModel):
    sender: str
    text: str

class ChatRequest(BaseModel):
    query: str
    limit: int = 8
    history: List[ChatMessage] = []

from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
def post_chat(request: ChatRequest):
    """Answers a user question based on semantic similarity search context and streams the LLM logic."""
    query = request.query
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat query cannot be empty."
        )

    try:
        # 1. Compute query vector
        query_vector = LocalEmbeddingsCalculator.calculate_query_embedding(query)
        
        # 2. Search local vector database for matching context
        matches = VectorDatabaseManager.semantic_query("document_chunks", query_vector, query, request.limit)
        
        # 3. Generate stream response using local LLM connector
        from app.core.llm import LocalLLMConnector
        
        # Convert history models to dicts for the LLM
        history_dicts = [{"sender": msg.sender, "text": msg.text} for msg in request.history]
        
        def event_generator():
            # Send the retrieved sources first
            yield f"data: {json.dumps({'type': 'sources', 'sources': matches})}\n\n"
            
            # Stream the generated tokens from the LLM
            for token in LocalLLMConnector.generate_rag_answer_stream(query, matches, history_dicts):
                # Ensure the token doesn't break SSE framing
                safe_token = token.replace("\n", "\\n")
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"Chat generation failed for query '{query}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate RAG response: {str(e)}"
        )
