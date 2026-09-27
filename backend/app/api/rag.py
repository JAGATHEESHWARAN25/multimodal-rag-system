import logging
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File, Depends
from app.config import OCR_OUTPUT_DIR
from app.models.database import DatabaseManager, db_manager
from app.core.embeddings import LocalEmbeddingsCalculator
from app.core.vectordb import VectorDatabaseManager
from app.core.security import get_current_user, UserContext, Role, require_roles, authorize_document_classification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["RAG & Semantic Search"])

@router.post("/audio/transcribe")
async def transcribe_audio_query(
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user)
):
    """Transcribes a recorded voice query snippet from the frontend microphone using the local Whisper engine."""
    file_bytes = await file.read()
    from app.core.audio.engine import AudioTranscriptionEngine
    transcript = AudioTranscriptionEngine.transcribe_snippet(file_bytes)
    return {"transcript": transcript, "text": transcript}

@router.post("/images/{image_id}/index", status_code=status.HTTP_200_OK)
def index_document(image_id: str, current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN, Role.DOCUMENT_OFFICER, Role.INTELLIGENCE_ANALYST]))):
    """Manually triggers vector embedding generation and ChromaDB indexing for a document."""
    record = DatabaseManager.get_image(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document record not found in SQLite metadata registry."
        )

    # Document Authorization
    authorize_document_classification(current_user, record.get("classification", "PUBLIC"))

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
    limit: int = Query(5, description="Maximum number of relevant results to return"),
    current_user: UserContext = Depends(get_current_user)
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
        raw_matches = VectorDatabaseManager.semantic_query("document_chunks", query_vector, query, limit * 3) # Request more to allow filtering
        
        # Authorization Validation
        matches = []
        for match in raw_matches:
            doc_id = match["metadata"].get("document_id")
            doc = DatabaseManager.get_image(doc_id) if doc_id else None
            doc_class = doc.get("classification", "PUBLIC") if doc else "PUBLIC"
            try:
                authorize_document_classification(current_user, doc_class)
                matches.append(match)
                if len(matches) >= limit:
                    break
            except HTTPException:
                continue # Unauthorized content is silently skipped in search results
        
        from app.core.audit import AuditLogger
        AuditLogger.log(
            event_type="SEARCH",
            action="SEARCH_EXECUTED",
            user=current_user,
            status="SUCCESS",
            details={"query": query, "results_count": len(matches)}
        )
        return matches
    except Exception as e:
        logger.error(f"Semantic vector search failed for query '{query}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Semantic search index is currently unavailable."
        )

@router.get("/search/advanced")
def advanced_search(
    query: Optional[str] = Query(None, description="The search phrase to query against documents"),
    q: Optional[str] = Query(None, description="Alternative alias for query"),
    search_mode: str = Query("hybrid", description="Search mode: hybrid, semantic, or keyword"),
    modality: Optional[str] = Query(None, description="Filter by document modality (pdf, docx, pptx, xlsx, csv, txt, image, audio)"),
    modalities: Optional[str] = Query(None, description="Alternative alias for modality"),
    classification: Optional[str] = Query(None, description="Filter by classification level"),
    date_from: Optional[str] = Query(None, description="Filter by upload start date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Alternative alias for date_from"),
    date_to: Optional[str] = Query(None, description="Filter by upload end date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Alternative alias for date_to"),
    entity: Optional[str] = Query(None, description="Filter by extracted entity mention"),
    document_id: Optional[str] = Query(None, description="Filter to specific document"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold"),
    sort_by: str = Query("relevance", description="Sort order: relevance, date_desc, date_asc"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Executes a high-precision Advanced Search combining dense vector similarity with
    relational keyword search (Reciprocal Rank Fusion) and multi-dimensional filters.
    Strictly enforces RBAC and classification clearance at every step.
    """
    import sqlite3
    effective_query = (query or q or "").strip()
    if not effective_query and not entity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")
    clean_query = effective_query or (entity or "")
    effective_modality = modalities or modality
    effective_date_from = start_date or date_from
    effective_date_to = end_date or date_to

    candidate_results = {}  # chunk_id -> dict

    # 1. Semantic Vector Retrieval
    if search_mode in ["semantic", "hybrid"]:
        try:
            query_vector = LocalEmbeddingsCalculator.calculate_query_embedding(clean_query)
            vector_matches = VectorDatabaseManager.semantic_query("document_chunks", query_vector, clean_query, limit * 3)
            for rank, vm in enumerate(vector_matches):
                cid = vm.get("chunk_id")
                if not cid:
                    continue
                # RRF score: 1 / (60 + rank)
                rrf_score = 1.0 / (60.0 + rank)
                candidate_results[cid] = {
                    "chunk_id": cid,
                    "text": vm.get("text", ""),
                    "score": vm.get("score", 0.0),
                    "rrf_score": rrf_score,
                    "metadata": vm.get("metadata", {}),
                    "source_type": "vector"
                }
        except Exception as e:
            logger.warning(f"Vector search failed during advanced search: {e}")

    # 2. Relational Keyword Retrieval (SQLite LIKE on knowledge_objects)
    if search_mode in ["keyword", "hybrid"]:
        try:
            with db_manager._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                keywords = [k.strip() for k in clean_query.split() if len(k.strip()) > 2]
                if not keywords:
                    keywords = [clean_query]
                
                like_clauses = " OR ".join(["content LIKE ?"] * len(keywords))
                params = [f"%{k}%" for k in keywords]
                
                cursor.execute(f"""
                    SELECT ko.id, ko.document_id, ko.content, ko.metadata_json, ko.object_type,
                           d.filename, d.classification, d.modality, COALESCE(d.uploaded_at, d.created_at) as uploaded_at
                    FROM knowledge_objects ko
                    JOIN documents d ON ko.document_id = d.id
                    WHERE ({like_clauses})
                    LIMIT {limit * 3}
                """, params)
                
                for rank, row in enumerate(cursor.fetchall()):
                    cid = row["id"]
                    rrf_score = 1.0 / (60.0 + rank)
                    meta = {}
                    if row["metadata_json"]:
                        try:
                            import json
                            meta = json.loads(row["metadata_json"])
                        except Exception:
                            pass
                    meta["source_file"] = row["filename"]
                    meta["document_id"] = row["document_id"]
                    meta["classification"] = row["classification"]
                    meta["modality"] = row["modality"]
                    meta["page_number"] = meta.get("page_number", 1)
                    meta["uploaded_at"] = row["uploaded_at"]

                    if cid in candidate_results:
                        candidate_results[cid]["rrf_score"] += rrf_score
                        candidate_results[cid]["source_type"] = "hybrid"
                    else:
                        candidate_results[cid] = {
                            "chunk_id": cid,
                            "text": row["content"] or "",
                            "score": 0.85,
                            "rrf_score": rrf_score,
                            "metadata": meta,
                            "source_type": "keyword"
                        }
        except Exception as e:
            logger.warning(f"Keyword search failed during advanced search: {e}")

    # 3. Authorization, Metadata Extraction & Multi-Filter Application
    filtered_results = []
    
    for item in candidate_results.values():
        meta = item.get("metadata", {})
        doc_id = meta.get("document_id")
        
        # Resolve document record if missing in metadata
        doc = DatabaseManager.get_image(doc_id) if doc_id else None
        if not doc and doc_id:
            continue
            
        doc_class = (doc.get("classification") if doc else meta.get("classification")) or "PUBLIC"
        doc_modality = (doc.get("modality") if doc else meta.get("modality")) or "unknown"
        doc_uploaded_at = (doc.get("uploaded_at") if doc else meta.get("uploaded_at")) or ""
        doc_filename = (doc.get("filename") if doc else meta.get("source_file")) or "document"

        # RBAC Classification Clearance Check
        try:
            authorize_document_classification(current_user, doc_class)
        except HTTPException:
            continue  # Silently skip unauthorized content to prevent data leakage

        # Filter: Modality
        if effective_modality:
            allowed_mods = [m.strip().lower() for m in effective_modality.split(",")]
            if doc_modality.lower() not in allowed_mods:
                continue

        # Filter: Specific Classification level
        if classification and doc_class.upper() != classification.upper():
            continue

        # Filter: Specific Document ID
        if document_id and doc_id != document_id:
            continue

        # Filter: Date range
        if effective_date_from and str(doc_uploaded_at)[:10] < effective_date_from:
            continue
        if effective_date_to and str(doc_uploaded_at)[:10] > effective_date_to:
            continue

        # Filter: Minimum confidence threshold
        if min_confidence is not None and item.get("score", 1.0) < min_confidence:
            continue

        # Filter: Mentioned Entity
        if entity:
            ent_match = False
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM knowledge_objects 
                    WHERE document_id = ? AND object_type = 'entity' AND content LIKE ?
                """, (doc_id, f"%{entity}%"))
                if cursor.fetchone():
                    ent_match = True
            if not ent_match:
                continue

        # Generate highlighted snippet (surround query term with <mark>)
        raw_text = item.get("text", "")
        snippet = raw_text[:280] + ("..." if len(raw_text) > 280 else "")

        item["metadata"]["document_id"] = doc_id
        item["metadata"]["source_file"] = doc_filename
        item["metadata"]["classification"] = doc_class
        item["metadata"]["modality"] = doc_modality
        item["metadata"]["uploaded_at"] = doc_uploaded_at
        item["snippet"] = snippet

        filtered_results.append(item)

    # 4. Sorting
    if sort_by == "date_desc":
        filtered_results.sort(key=lambda x: str(x.get("metadata", {}).get("uploaded_at") or ""), reverse=True)
    elif sort_by == "date_asc":
        filtered_results.sort(key=lambda x: str(x.get("metadata", {}).get("uploaded_at") or ""))
    else:  # relevance
        filtered_results.sort(key=lambda x: x.get("rrf_score", 0.0), reverse=True)

    final_results = filtered_results[:limit]

    # 5. Audit Logging
    from app.core.audit import AuditLogger
    AuditLogger.log(
        event_type="SEARCH",
        action="ADVANCED_SEARCH_EXECUTED",
        user=current_user,
        status="SUCCESS",
        details={
            "query": clean_query,
            "search_mode": search_mode,
            "modality": modality,
            "classification": classification,
            "results_count": len(final_results)
        }
    )

    return {
        "query": clean_query,
        "search_mode": search_mode,
        "total_matches": len(final_results),
        "results": final_results
    }

from pydantic import BaseModel
from typing import List, Optional
import uuid

class ChatMessage(BaseModel):
    sender: str
    text: str

class ChatSessionCreate(BaseModel):
    title: str

class ChatRequest(BaseModel):
    query: str
    file_ids: Optional[List[str]] = None
    limit: int = 8
    history: List[ChatMessage] = []
    session_id: Optional[str] = None
    use_graph_expansion: bool = True

@router.post("/chat/sessions")
def create_chat_session(request: ChatSessionCreate, current_user: UserContext = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    db_manager.create_chat_session(session_id, current_user.id, request.title)
    
    from app.core.audit import AuditLogger
    AuditLogger.log(
        event_type="CHAT",
        action="CHAT_SESSION_CREATED",
        user=current_user,
        resource_type="chat_session",
        resource_id=session_id,
        status="SUCCESS",
        details={"title": request.title}
    )
    return {"id": session_id, "title": request.title}

@router.get("/chat/sessions")
def list_chat_sessions(current_user: UserContext = Depends(get_current_user)):
    return db_manager.get_chat_sessions(current_user.id)

@router.get("/chat/sessions/{session_id}")
def get_chat_session_history(session_id: str, current_user: UserContext = Depends(get_current_user)):
    session = db_manager.get_chat_session(session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
    messages = db_manager.get_chat_messages(session_id)
    return {"session": session, "messages": messages}

@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: str, current_user: UserContext = Depends(get_current_user)):
    deleted = db_manager.delete_chat_session(session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    from app.core.audit import AuditLogger
    AuditLogger.log(
        event_type="CHAT",
        action="CHAT_SESSION_DELETED",
        user=current_user,
        resource_type="chat_session",
        resource_id=session_id,
        status="SUCCESS",
        details={"session_id": session_id}
    )
    return {"status": "success", "message": "Session deleted"}


from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
def post_chat(request: ChatRequest, current_user: UserContext = Depends(get_current_user)):
    """Answers a user question based on multimodal input, vector search, graph reasoning, and streams the answer."""
    query = request.query
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat query cannot be empty."
        )

    try:
        from app.core.audit import AuditLogger
        from app.core.rag.universal_query import UniversalMultimodalQueryService

        AuditLogger.log(
            event_type="CHAT",
            action="MULTIMODAL_QUERY_STARTED",
            user=current_user,
            status="SUCCESS",
            details={"query": query, "file_ids": request.file_ids or []}
        )

        history_dicts = []
        if request.session_id:
            session = db_manager.get_chat_session(request.session_id, current_user.id)
            if not session:
                raise HTTPException(status_code=403, detail="Session not found or unauthorized")
            
            # Auto-title session if current title is default or generic
            if session.get("title") in ["New Chat Session", "New Chat", "Untitled", ""]:
                clean_title = query.strip()
                if len(clean_title) > 36:
                    clean_title = clean_title[:36] + "..."
                db_manager.update_chat_session_title(request.session_id, clean_title)
            
            past_messages = db_manager.get_chat_messages(request.session_id)
            MEMORY_WINDOW = 10
            for msg in past_messages[-MEMORY_WINDOW:]:
                history_dicts.append({"sender": msg["role"], "text": msg["content"]})
                
            user_msg_id = str(uuid.uuid4())
            db_manager.add_chat_message(user_msg_id, request.session_id, "user", query)
        else:
            history_dicts = [{"sender": msg.sender, "text": msg.text} for msg in request.history]

        result = UniversalMultimodalQueryService.execute_query(
            query=query,
            user_context=current_user,
            file_ids=request.file_ids,
            session_id=request.session_id,
            limit=request.limit,
            history=history_dicts,
            use_graph_expansion=request.use_graph_expansion
        )

        AuditLogger.log(
            event_type="CHAT",
            action="RELATED_KNOWLEDGE_RETRIEVED",
            user=current_user,
            status="SUCCESS",
            details={
                "trace_id": result["trace_id"],
                "related_docs": len(result["related_documents"]),
                "related_images": len(result["related_images"]),
                "related_entities": len(result["related_entities"]),
                "relationships": len(result["relationships"])
            }
        )

        def event_generator():
            # 1. Emit Input Summary Event
            yield f"data: {json.dumps({'type': 'input_summary', 'summary': result['input_summary']})}\n\n"

            # 2. Emit Related Knowledge Event
            yield f"data: {json.dumps({'type': 'related_knowledge', 'related_documents': result['related_documents'], 'related_images': result['related_images'], 'related_entities': result['related_entities'], 'relationships': result['relationships']})}\n\n"

            # 3. Emit Sources / Citations Event
            citations = result.get("citations", [])
            yield f"data: {json.dumps({'type': 'sources', 'sources': citations})}\n\n"
            
            # 4. Stream Tokens
            full_response = ""
            for token in result["answer_stream"]:
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            # 5. Emit Confidence Event
            confidence = result.get("evidence_confidence", {})
            yield f"data: {json.dumps({'type': 'confidence', 'confidence': confidence})}\n\n"

            # 6. Emit Timing Performance Event
            if "timing_breakdown" in result:
                yield f"data: {json.dumps({'type': 'timing', 'timing': result['timing_breakdown']})}\n\n"
            
            # Persist assistant response if part of a session
            if request.session_id:
                asst_msg_id = str(uuid.uuid4())
                db_manager.add_chat_message(asst_msg_id, request.session_id, "assistant", full_response, citations_json=json.dumps(citations))
            
            AuditLogger.log(
                event_type="CHAT",
                action="MULTIMODAL_QUERY_COMPLETED",
                user=current_user,
                status="SUCCESS",
                details={"trace_id": result["trace_id"], "query": query, "response_length": len(full_response), "session_id": request.session_id}
            )
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"Universal Multimodal Chat error: {str(e)}")
        
        from app.core.audit import AuditLogger
        AuditLogger.log(
            event_type="CHAT",
            action="MULTIMODAL_QUERY_FAILED",
            user=current_user,
            status="FAILED",
            details={"query": query, "error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Multimodal RAG response: {str(e)}"
        )

