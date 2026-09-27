import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.core.security import get_current_user, UserContext, Role, require_roles
from app.models.database import db_manager

router = APIRouter(prefix="/api", tags=["System Dashboard"])

@router.get("/system/dashboard")
@router.get("/dashboard")
def get_dashboard(current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN, Role.INTELLIGENCE_ANALYST, Role.DOCUMENT_OFFICER, Role.AUDITOR]))):
    """Returns comprehensive intelligence metrics for the Final Review Intelligence Dashboard."""
    stats = {}
    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Total docs
        cursor.execute("SELECT COUNT(*) as c FROM documents")
        stats["total_documents"] = cursor.fetchone()["c"]
        
        # Modality distribution
        cursor.execute("SELECT modality, COUNT(*) as c FROM documents GROUP BY modality")
        mod_counts = {row["modality"] or "unknown": row["c"] for row in cursor.fetchall()}
        for m in ["pdf", "docx", "pptx", "xlsx", "csv", "txt", "image", "audio"]:
            if m not in mod_counts:
                mod_counts[m] = 0
        stats["modality_distribution"] = mod_counts
        
        # Classification distribution
        cursor.execute("SELECT classification, COUNT(*) as c FROM documents GROUP BY classification")
        stats["classification_distribution"] = {row["classification"] or "PUBLIC": row["c"] for row in cursor.fetchall()}
        
        # Jobs breakdown
        cursor.execute("SELECT status, COUNT(*) as c FROM background_jobs GROUP BY status")
        stats["jobs"] = {row["status"]: row["c"] for row in cursor.fetchall()}
        
        # Graph nodes total and by type
        cursor.execute("SELECT COUNT(*) as c FROM knowledge_objects")
        stats["graph_nodes"] = cursor.fetchone()["c"]
        cursor.execute("SELECT object_type, COUNT(*) as c FROM knowledge_objects GROUP BY object_type")
        stats["graph_nodes_by_type"] = {row["object_type"]: row["c"] for row in cursor.fetchall()}
        
        # Graph edges total and by type
        cursor.execute("SELECT COUNT(*) as c FROM relationship_edges")
        stats["graph_edges"] = cursor.fetchone()["c"]
        cursor.execute("SELECT relationship_type, COUNT(*) as c FROM relationship_edges GROUP BY relationship_type")
        stats["graph_edges_by_type"] = {row["relationship_type"]: row["c"] for row in cursor.fetchall()}
        
        # Users
        cursor.execute("SELECT COUNT(*) as c FROM users")
        stats["total_users"] = cursor.fetchone()["c"]

        # Cache metrics
        cursor.execute("SELECT metric_name, metric_value FROM system_metrics")
        stats["cache_metrics"] = {row["metric_name"]: row["metric_value"] for row in cursor.fetchall()}
        
        # Recent documents (latest 6)
        cursor.execute("""
            SELECT id, filename, modality, classification, status, created_at as uploaded_at 
            FROM documents 
            ORDER BY created_at DESC LIMIT 6
        """)
        stats["recent_documents"] = [dict(row) for row in cursor.fetchall()]
        
        # Recent audit activity (latest 8)
        cursor.execute("""
            SELECT id, event_type, action, username, status, timestamp 
            FROM audit_logs 
            ORDER BY timestamp DESC LIMIT 8
        """)
        stats["recent_activity"] = [dict(row) for row in cursor.fetchall()]
        
        # Top extracted entities (top 8)
        cursor.execute("""
            SELECT content as name, COUNT(*) as count 
            FROM knowledge_objects 
            WHERE object_type = 'entity' 
            GROUP BY content 
            ORDER BY count DESC LIMIT 8
        """)
        stats["top_entities"] = [dict(row) for row in cursor.fetchall()]
        
    try:
        from app.core.resource_manager import ResourceManager
        rm = ResourceManager()
        stats["system_resources"] = rm.get_system_metrics()
    except Exception:
        stats["system_resources"] = {"ram_percent": 0.0, "cpu_percent": 0.0, "ram_available_gb": 0.0}
        
    return stats

@router.get("/timeline")
@router.get("/system/timeline")
def get_timeline(
    modality: Optional[str] = Query(None, description="Optional filter by document modality"),
    classification: Optional[str] = Query(None, description="Optional filter by classification"),
    event_type: Optional[str] = Query(None, description="Optional filter by event type"),
    limit: int = Query(50, ge=1, le=200, description="Max timeline events to return"),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Returns an aggregated, chronological timeline of system events respecting RBAC clearance.
    Combines document ingestion, processing stages, and authorized user audit logs.
    """
    from app.core.security import authorize_document_classification
    timeline = []
    
    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Document Ingestion Events
        cursor.execute("SELECT id, filename, modality, classification, created_at as uploaded_at, status FROM documents ORDER BY created_at DESC LIMIT 100")
        for doc in cursor.fetchall():
            doc_dict = dict(doc)
            try:
                authorize_document_classification(current_user, doc_dict.get("classification", "PUBLIC"))
                timeline.append({
                    "id": f"doc_{doc_dict['id']}",
                    "timestamp": doc_dict.get("uploaded_at"),
                    "category": "DOCUMENT_INGESTION",
                    "title": f"Document Ingested: {doc_dict.get('filename')}",
                    "details": f"Modality: {doc_dict.get('modality')}, Status: {doc_dict.get('status')}",
                    "document_id": doc_dict.get("id"),
                    "filename": doc_dict.get("filename"),
                    "modality": doc_dict.get("modality", "document"),
                    "classification": doc_dict.get("classification", "PUBLIC"),
                    "badge_color": "blue"
                })
            except Exception:
                continue
                
        # 2. Processing History Events (OCR, Chunking, Entity Extraction)
        cursor.execute("""
            SELECT ph.id, ph.document_id, ph.stage, ph.start_time, ph.duration_ms, ph.status, d.filename, d.classification, d.modality
            FROM processing_history ph
            JOIN documents d ON ph.document_id = d.id
            ORDER BY ph.start_time DESC LIMIT 100
        """)
        for ph in cursor.fetchall():
            ph_dict = dict(ph)
            try:
                authorize_document_classification(current_user, ph_dict.get("classification", "PUBLIC"))
                stage_name = ph_dict.get("stage", "Processing")
                timeline.append({
                    "id": f"ph_{ph_dict['id']}",
                    "timestamp": ph_dict.get("start_time"),
                    "category": "PROCESSING",
                    "title": f"{stage_name.upper()} Completed: {ph_dict.get('filename')}",
                    "details": f"Status: {ph_dict.get('status')}, Duration: {ph_dict.get('duration_ms', 0)}ms",
                    "document_id": ph_dict.get("document_id"),
                    "filename": ph_dict.get("filename"),
                    "modality": ph_dict.get("modality", "document"),
                    "classification": ph_dict.get("classification", "PUBLIC"),
                    "badge_color": "green"
                })
            except Exception:
                continue

        # 3. Audio Segment Milestones if any
        cursor.execute("""
            SELECT ko.id, ko.document_id, ko.content, ko.metadata_json, d.filename, d.classification, d.modality, d.created_at as uploaded_at
            FROM knowledge_objects ko
            JOIN documents d ON ko.document_id = d.id
            WHERE ko.object_type = 'audio_segment'
            ORDER BY d.created_at DESC LIMIT 50
        """)
        for arow in cursor.fetchall():
            adict = dict(arow)
            try:
                authorize_document_classification(current_user, adict.get("classification", "PUBLIC"))
                ameta = {}
                if adict.get("metadata_json"):
                    try:
                        import json
                        ameta = json.loads(adict["metadata_json"])
                    except Exception:
                        pass
                timeline.append({
                    "id": f"audio_{adict['id']}",
                    "timestamp": adict.get("uploaded_at"),
                    "category": "AUDIO_UTTERANCE",
                    "title": f"Audio Utterance: {adict.get('filename')}",
                    "description": adict.get("content", ""),
                    "snippet": adict.get("content", ""),
                    "start_sec": ameta.get("start_sec", 0),
                    "end_sec": ameta.get("end_sec", 0),
                    "document_id": adict.get("document_id"),
                    "filename": adict.get("filename"),
                    "modality": "audio",
                    "classification": adict.get("classification", "PUBLIC"),
                    "badge_color": "purple"
                })
            except Exception:
                continue

        # 4. User Activity Events from Audit Logs (Searches, Chat, Graph Reasoning)
        cursor.execute("""
            SELECT id, event_type, action, username, resource_id, status, timestamp, details
            FROM audit_logs
            WHERE event_type IN ('CHAT', 'SEARCH', 'GRAPH', 'DOCUMENT')
            ORDER BY timestamp DESC LIMIT 100
        """)
        for al in cursor.fetchall():
            al_dict = dict(al)
            action = al_dict.get("action", "ACTION")
            timeline.append({
                "id": f"al_{al_dict['id']}",
                "timestamp": al_dict.get("timestamp"),
                "category": al_dict.get("event_type", "AUDIT"),
                "title": f"{action.replace('_', ' ').title()}",
                "details": f"User: {al_dict.get('username')}, Status: {al_dict.get('status')}",
                "document_id": al_dict.get("resource_id"),
                "classification": "INTERNAL",
                "badge_color": "green"
            })

    # Sort all events chronologically descending
    timeline.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    
    # Filter by modality if specified
    if modality:
        timeline = [e for e in timeline if (e.get("modality") or "").lower() == modality.lower()]

    # Filter by classification if specified
    if classification:
        timeline = [e for e in timeline if (e.get("classification") or "").upper() == classification.upper()]

    # Filter by event_type if specified
    if event_type:
        timeline = [e for e in timeline if e.get("category", "").lower() == event_type.lower()]
        
    result = timeline[:limit]
    return {
        "events": result,
        "timeline": result,
        "total": len(result)
    }

@router.get("/audit")
def get_audit_logs(current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))):
    """Returns recent audit logs for System Admins."""
    logs = []
    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100")
        for row in cursor.fetchall():
            logs.append(dict(row))
            
    return logs

import csv
import io
import json
from fastapi import Query
from fastapi.responses import Response

@router.get("/audit/export")
def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$"),
    current_user: UserContext = Depends(require_roles([Role.SYSTEM_ADMIN]))
):
    """Exports audit logs as CSV or JSON for compliance."""
    logs = []
    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC")
        for row in cursor.fetchall():
            logs.append(dict(row))

    if format == "json":
        return Response(
            content=json.dumps(logs, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"}
        )

    output = io.StringIO()
    if logs:
        fieldnames = list(logs[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for log in logs:
            writer.writerow({k: str(v) if v is not None else "" for k, v in log.items()})
    else:
        writer = csv.writer(output)
        writer.writerow(["id", "user_id", "username", "role", "event_type", "action", "resource_type", "resource_id", "status", "ip_address", "request_id", "details", "timestamp"])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
    )

