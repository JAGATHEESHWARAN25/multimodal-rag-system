from fastapi import APIRouter, HTTPException, Depends, status, Query
from app.core.security import get_current_user, UserContext, authorize_document_classification
from app.models.database import db_manager
from app.core.summarization import DocumentSummarizer
from app.core.audit import AuditLogger

router = APIRouter(prefix="/api/documents", tags=["Summarization"])

@router.post("/{document_id}/summarize", status_code=status.HTTP_200_OK)
def summarize_document(
    document_id: str, 
    force_refresh: bool = Query(False, description="Bypass cache and regenerate summary"),
    current_user: UserContext = Depends(get_current_user)
):
    # 1. Fetch document metadata to check authorization
    doc = db_manager.get_image(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_class = doc.get("classification", "PUBLIC")
    authorize_document_classification(current_user, doc_class)

    # Check if cached prior to calling
    was_cached = False
    if not force_refresh:
        existing = db_manager.get_document_summary(document_id)
        if existing:
            was_cached = True
    
    # 2. Perform summarization (returns cached or freshly generated)
    summary = DocumentSummarizer.summarize_document(document_id, force_refresh=force_refresh)
    
    # 3. Log the action
    AuditLogger.log(
        event_type="SUMMARIZATION",
        action="DOCUMENT_SUMMARY_ACCESSED" if was_cached else "DOCUMENT_SUMMARIZED",
        user=current_user,
        status="SUCCESS",
        resource_id=document_id,
        details={"classification": doc_class, "cached": was_cached, "force_refresh": force_refresh}
    )
    
    return {"document_id": document_id, "summary": summary, "cached": was_cached}

@router.get("/{document_id}/summary", status_code=status.HTTP_200_OK)
def get_cached_summary(
    document_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    """Retrieves existing cached summary for a document without invoking LLM."""
    doc = db_manager.get_image(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_class = doc.get("classification", "PUBLIC")
    authorize_document_classification(current_user, doc_class)

    cached_summary = db_manager.get_document_summary(document_id)
    if not cached_summary:
        raise HTTPException(status_code=404, detail="No cached summary found for this document")

    AuditLogger.log(
        event_type="SUMMARIZATION",
        action="DOCUMENT_SUMMARY_READ",
        user=current_user,
        status="SUCCESS",
        resource_id=document_id,
        details={"classification": doc_class}
    )

    return {"document_id": document_id, "summary": cached_summary, "cached": True}

