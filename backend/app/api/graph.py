from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import sqlite3
import json
from app.core.security import get_current_user, UserContext, authorize_document_classification
from app.core.graph.manager import GraphManager
from app.models.database import db_manager
from app.core.audit import AuditLogger
from app.core.graph.reasoning import GraphReasoningEngine

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])

def _filter_authorized(nodes: list, current_user: UserContext) -> list:
    authorized_nodes = []
    for node in nodes:
        doc_id = node.get("document_id")
        doc_class = "PUBLIC"
        if doc_id:
            doc = db_manager.get_image(doc_id)
            if doc:
                doc_class = doc.get("classification", "PUBLIC")
                if "filename" in doc and "document_filename" not in node:
                    node["document_filename"] = doc["filename"]
        try:
            authorize_document_classification(current_user, doc_class)
            # Parse json fields for clean client consumption
            if node.get("metadata_json") and not isinstance(node.get("metadata"), dict):
                try:
                    node["metadata"] = json.loads(node["metadata_json"])
                except Exception:
                    pass
            if node.get("bounding_box") and not isinstance(node.get("bounding_box"), (dict, list)):
                try:
                    node["bounding_box"] = json.loads(node["bounding_box"])
                except Exception:
                    pass
            authorized_nodes.append(node)
        except HTTPException:
            continue
    return authorized_nodes

@router.get("/nodes/{node_id}")
def get_node(node_id: str, current_user: UserContext = Depends(get_current_user)):
    node = GraphManager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    auth_nodes = _filter_authorized([node], current_user)
    if not auth_nodes:
        raise HTTPException(status_code=403, detail="Unauthorized access to graph node")
        
    AuditLogger.log(
        event_type="GRAPH",
        action="NODE_INSPECTED",
        user=current_user,
        resource_type="knowledge_object",
        resource_id=node_id,
        status="SUCCESS",
        details={"object_type": node.get("object_type", "UNKNOWN")}
    )
    return auth_nodes[0]

@router.get("/nodes/{node_id}/children")
def get_children(node_id: str, type: Optional[str] = None, current_user: UserContext = Depends(get_current_user)):
    children = GraphManager.find_children(node_id, type)
    return _filter_authorized(children, current_user)

@router.get("/nodes/{node_id}/parents")
def get_parents(node_id: str, type: Optional[str] = None, current_user: UserContext = Depends(get_current_user)):
    parents = GraphManager.find_parent(node_id, type)
    return _filter_authorized(parents, current_user)

@router.get("/nodes/{node_id}/neighbors")
def get_neighbors(node_id: str, depth: int = 1, type: Optional[str] = None, current_user: UserContext = Depends(get_current_user)):
    if depth > 3:
        depth = 3 # Cap traversal depth for performance
    neighbors = GraphManager.find_neighbors(node_id, depth, type)
    return _filter_authorized(neighbors, current_user)

@router.get("/visualize")
def visualize_graph(
    node_type: Optional[str] = None,
    relationship_type: Optional[str] = None,
    document_id: Optional[str] = None,
    limit: int = 500,
    current_user: UserContext = Depends(get_current_user)
):
    """Returns nodes and edges authorized for the current user for graph visualization with optional filters."""
    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge_objects WHERE 1=1"
        params = []
        if node_type:
            query += " AND object_type = ?"
            params.append(node_type)
        if document_id:
            query += " AND document_id = ?"
            params.append(document_id)
        query += f" LIMIT {min(1000, limit)}"
        
        cursor.execute(query, params)
        raw_nodes = [dict(row) for row in cursor.fetchall()]
        auth_nodes = _filter_authorized(raw_nodes, current_user)
        auth_ids = {n["id"] for n in auth_nodes}
        
        edge_query = "SELECT * FROM relationship_edges WHERE 1=1"
        edge_params = []
        if relationship_type:
            edge_query += " AND relationship_type = ?"
            edge_params.append(relationship_type)
        edge_query += " LIMIT 1500"
        
        cursor.execute(edge_query, edge_params)
        raw_edges = [dict(row) for row in cursor.fetchall()]
        auth_edges = [e for e in raw_edges if e["source_id"] in auth_ids and e["target_id"] in auth_ids]

        AuditLogger.log(
            event_type="GRAPH",
            action="GRAPH_VISUALIZED",
            user=current_user,
            resource_type="knowledge_graph",
            status="SUCCESS",
            details={"node_count": len(auth_nodes), "edge_count": len(auth_edges)}
        )
        
        return {"nodes": auth_nodes, "edges": auth_edges}

@router.get("/entities/{entity_name}/profile")
def get_entity_profile(entity_name: str, current_user: UserContext = Depends(get_current_user)):
    """
    Returns a dedicated Intelligence Profile for a named entity.
    Includes occurrences, source documents, connected relationships, related entities,
    and relevant text chunks, strictly filtered by RBAC clearance.
    """
    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Fetch matching entity nodes
        cursor.execute("""
            SELECT ko.*, d.filename, d.classification, d.modality
            FROM knowledge_objects ko
            JOIN documents d ON ko.document_id = d.id
            WHERE ko.object_type = 'entity' AND LOWER(ko.content) = LOWER(?)
        """, (entity_name,))
        matching_nodes = [dict(row) for row in cursor.fetchall()]
        if not matching_nodes:
            cursor.execute("""
                SELECT ko.*, d.filename, d.classification, d.modality
                FROM knowledge_objects ko
                JOIN documents d ON ko.document_id = d.id
                WHERE ko.object_type = 'entity' AND LOWER(ko.content) LIKE LOWER(?)
            """, (f"%{entity_name}%",))
            matching_nodes = [dict(row) for row in cursor.fetchall()]
        
        auth_entity_nodes = _filter_authorized(matching_nodes, current_user)
        if not auth_entity_nodes:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found or unauthorized.")
            
        doc_ids = list({n["document_id"] for n in auth_entity_nodes})
        entity_type = "ENTITY"
        for n in auth_entity_nodes:
            if n.get("metadata") and isinstance(n["metadata"], dict):
                entity_type = n["metadata"].get("entity_type", entity_type)
                break

        # 2. Source Documents
        source_docs = []
        for did in doc_ids:
            doc = db_manager.get_image(did)
            if doc:
                try:
                    authorize_document_classification(current_user, doc.get("classification", "PUBLIC"))
                    source_docs.append({
                        "id": doc["id"],
                        "filename": doc["filename"],
                        "modality": doc.get("modality", "unknown"),
                        "classification": doc.get("classification", "PUBLIC"),
                        "uploaded_at": doc.get("uploaded_at")
                    })
                except Exception:
                    pass

        # 3. Direct Relationships & Connected Entities
        entity_node_ids = [n["id"] for n in auth_entity_nodes]
        placeholders = ",".join(["?"] * len(entity_node_ids))
        
        cursor.execute(f"""
            SELECT re.relationship_type, ko_target.content as target_name, ko_target.object_type as target_type,
                   ko_target.id as target_id, d.filename as source_file, d.classification
            FROM relationship_edges re
            JOIN knowledge_objects ko_target ON re.target_id = ko_target.id
            JOIN documents d ON ko_target.document_id = d.id
            WHERE re.source_id IN ({placeholders})
        """, entity_node_ids)
        
        raw_outgoing = [dict(r) for r in cursor.fetchall()]
        auth_outgoing = []
        for r in raw_outgoing:
            try:
                authorize_document_classification(current_user, r.get("classification", "PUBLIC"))
                auth_outgoing.append({
                    "relationship": r["relationship_type"],
                    "target_name": r["target_name"],
                    "target_type": r["target_type"],
                    "source_file": r["source_file"]
                })
            except Exception:
                pass

        # 4. Relevant text chunks / audio segments containing the entity
        cursor.execute(f"""
            SELECT ko.id, ko.content, ko.metadata_json, ko.object_type, d.filename, d.classification
            FROM knowledge_objects ko
            JOIN documents d ON ko.document_id = d.id
            WHERE ko.document_id IN ({','.join(['?'] * len(doc_ids))})
              AND ko.object_type IN ('paragraph', 'text', 'audio_segment', 'chunk', 'heading')
              AND ko.content LIKE ?
            LIMIT 5
        """, doc_ids + [f"%{entity_name}%"])
        
        raw_chunks = [dict(r) for r in cursor.fetchall()]
        auth_chunks = []
        for c in raw_chunks:
            try:
                authorize_document_classification(current_user, c.get("classification", "PUBLIC"))
                cmeta = {}
                if c.get("metadata_json"):
                    try:
                        import json
                        cmeta = json.loads(c["metadata_json"])
                    except Exception:
                        pass
                auth_chunks.append({
                    "id": c["id"],
                    "source_file": c["filename"],
                    "page_number": cmeta.get("page_number", 1),
                    "block_type": c.get("object_type", "chunk"),
                    "text": (c["content"] or "")[:250] + ("..." if len(c["content"] or "") > 250 else "")
                })
            except Exception:
                pass

    AuditLogger.log(
        event_type="GRAPH",
        action="ENTITY_PROFILE_INSPECTED",
        user=current_user,
        resource_type="entity",
        resource_id=entity_name,
        status="SUCCESS",
        details={"entity_name": entity_name, "occurrences": len(auth_entity_nodes)}
    )

    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "total_occurrences": len(auth_entity_nodes),
        "mention_count": len(auth_entity_nodes),
        "source_documents": source_docs,
        "documents": source_docs,
        "relationships": auth_outgoing,
        "relevant_chunks": auth_chunks
    }

from pydantic import BaseModel

class NLGraphQueryRequest(BaseModel):
    query: str
    max_depth: int = 2

@router.post("/query")
def natural_language_graph_query(
    request: NLGraphQueryRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Translates a natural language graph query into safe deterministic graph operations.
    Enforces bounded traversal depth, max result caps, and strict RBAC clearance.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    from app.core.nlp.advanced_entity_extractor import AdvancedLocalEntityExtractor
    extractor = AdvancedLocalEntityExtractor()
    extracted_entities = extractor.extract_entities(query)
    
    entity_names = [e["value"] for e in extracted_entities]
    matched_nodes = []
    matched_edges = []
    summary_lines = []

    with db_manager._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # If entities found in query, search graph around those entities
        if entity_names:
            for ent_name in entity_names[:2]:
                cursor.execute("""
                    SELECT ko.*, d.filename, d.classification 
                    FROM knowledge_objects ko
                    JOIN documents d ON ko.document_id = d.id
                    WHERE ko.object_type = 'entity' AND LOWER(ko.content) = LOWER(?)
                """, (ent_name,))
                entity_kos = [dict(r) for r in cursor.fetchall()]
                auth_kos = _filter_authorized(entity_kos, current_user)
                matched_nodes.extend(auth_kos)
                
                # Expand 1-hop neighbors
                for n in auth_kos:
                    neighbors = GraphReasoningEngine.find_neighbors(n["id"], depth=min(2, request.max_depth))
                    auth_neighbors = _filter_authorized(neighbors, current_user)
                    matched_nodes.extend(auth_neighbors)
                    
            summary_lines.append(f"Discovered Knowledge Graph nodes connected to {', '.join(entity_names)}.")
        else:
            # Fallback: Search entity nodes matching words in query
            words = [w for w in query.split() if len(w) > 3]
            if words:
                like_clause = " OR ".join(["content LIKE ?"] * len(words))
                cursor.execute(f"""
                    SELECT ko.*, d.filename, d.classification 
                    FROM knowledge_objects ko
                    JOIN documents d ON ko.document_id = d.id
                    WHERE ko.object_type = 'entity' AND ({like_clause})
                    LIMIT 20
                """, [f"%{w}%" for w in words])
                raw_matches = [dict(r) for r in cursor.fetchall()]
                matched_nodes.extend(_filter_authorized(raw_matches, current_user))
                summary_lines.append(f"Located relevant entities matching query terms: {', '.join(words)}.")
            else:
                summary_lines.append("No specific entities or relationships matched the query.")

        # Deduplicate nodes
        seen_node_ids = set()
        unique_nodes = []
        for node in matched_nodes:
            if node["id"] not in seen_node_ids:
                seen_node_ids.add(node["id"])
                unique_nodes.append(node)
                
        # Find connecting edges between discovered nodes
        if unique_nodes:
            id_list = list(seen_node_ids)[:100]
            placeholders = ",".join(["?"] * len(id_list))
            cursor.execute(f"""
                SELECT * FROM relationship_edges 
                WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
                LIMIT 50
            """, id_list + id_list)
            matched_edges = [dict(r) for r in cursor.fetchall()]

    AuditLogger.log(
        event_type="GRAPH",
        action="NL_GRAPH_QUERY_EXECUTED",
        user=current_user,
        status="SUCCESS",
        details={"query": query, "nodes_found": len(unique_nodes), "edges_found": len(matched_edges)}
    )

    return {
        "query": query,
        "summary": " ".join(summary_lines),
        "nodes": unique_nodes,
        "edges": matched_edges,
        "total_nodes": len(unique_nodes),
        "total_edges": len(matched_edges)
    }

@router.get("/reason")
def reason_graph(
    source_id: str,
    target_id: Optional[str] = None,
    max_depth: int = 3,
    current_user: UserContext = Depends(get_current_user)
):
    AuditLogger.log(
        event_type="GRAPH",
        action="GRAPH_REASONED",
        user=current_user,
        resource_type="knowledge_graph",
        status="SUCCESS",
        details={"source_id": source_id, "target_id": target_id, "max_depth": max_depth}
    )

    if target_id:
        path_nodes = GraphReasoningEngine.find_path(source_id, target_id, max_depth=max_depth, user_role=current_user.role)
        return {"mode": "path", "path": _filter_authorized(path_nodes, current_user)}
    else:
        neighbors = GraphReasoningEngine.find_neighbors(source_id, depth=max_depth)
        related_entities = GraphReasoningEngine.find_related_entities(source_id, user_role=current_user.role)
        parent_docs = GraphReasoningEngine.find_documents_containing_entity(source_id, user_role=current_user.role)
        
        return {
            "mode": "neighborhood",
            "neighbors": _filter_authorized(neighbors, current_user),
            "related_entities": _filter_authorized(related_entities, current_user),
            "parent_documents": _filter_authorized(parent_docs, current_user)
        }


