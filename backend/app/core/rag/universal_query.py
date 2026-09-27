import uuid
import time
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models.database import db_manager, DatabaseManager
from app.core.security import UserContext, authorize_document_classification
from app.core.vectordb import VectorDatabaseManager
from app.core.embeddings import LocalEmbeddingsCalculator
from app.core.graph.reasoning import GraphReasoningEngine
from app.core.graph.manager import GraphManager
from app.core.rag.scoring import EvidenceScorer
from app.core.rag.agents import ModularMultiAgentPipeline, AgentContext
from app.core.nlp.advanced_entity_extractor import AdvancedLocalEntityExtractor

logger = logging.getLogger(__name__)

class RelatedAsset(BaseModel):
    document_id: str
    filename: str
    modality: str
    classification: str
    relevance_score: float = 1.0
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    thumbnail_url: Optional[str] = None

class RelatedEntity(BaseModel):
    name: str
    entity_type: str
    mention_count: int = 1
    source_documents: List[str] = Field(default_factory=list)

class GraphRelationship(BaseModel):
    source_name: str
    relationship: str
    target_name: str
    confidence: float = 1.0

class UniversalMultimodalResponse(BaseModel):
    trace_id: str
    query: str
    input_summary: str
    answer: str = ""
    evidence_confidence: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    related_documents: List[RelatedAsset] = Field(default_factory=list)
    related_images: List[RelatedAsset] = Field(default_factory=list)
    related_entities: List[RelatedEntity] = Field(default_factory=list)
    relationships: List[GraphRelationship] = Field(default_factory=list)
    input_objects: List[Dict[str, Any]] = Field(default_factory=list)
    timing_breakdown: Optional[Dict[str, Any]] = Field(default_factory=dict)

class UniversalMultimodalQueryService:
    """Unified service orchestrating multimodal query analysis, hybrid retrieval, pre-LLM RBAC filtering, and related knowledge discovery."""

    @classmethod
    def execute_query(
        cls,
        query: str,
        user_context: UserContext,
        file_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
        history: Optional[List[Dict[str, str]]] = None,
        use_graph_expansion: bool = True
    ) -> Dict[str, Any]:
        
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        t_pipeline_start = time.perf_counter()
        logger.info(f"[{trace_id}] UniversalMultimodalQueryService executing query for user {user_context.username} ({user_context.role})")
        
        if file_ids is None:
            file_ids = []
            
        # Check if the query asks for a summary of a specific document in the global index
        is_summarize_query = any(keyword in query.lower() for keyword in ["summarize", "summary", "overview", "tl;dr"])
        if is_summarize_query and not file_ids:
            all_docs = db_manager.get_all_images()
            for d in all_docs:
                if d.get("filename") and d["filename"].lower() in query.lower():
                    file_ids.append(d["id"])
            
        # 1. Resolve Input Documents & Verify Ownership / RBAC
        t_entity_start = time.perf_counter()
        input_docs = []
        input_summaries = []
        extracted_query_entities = []
        
        extractor = AdvancedLocalEntityExtractor()
        extracted_query_entities.extend(extractor.extract_entities(query))
        
        for fid in file_ids:
            doc = db_manager.get_image(fid)
            if doc:
                try:
                    authorize_document_classification(user_context, doc.get("classification", "PUBLIC"))
                    input_docs.append(doc)
                    
                    # Generate input summary for each attached document
                    modality = doc.get("modality", "unknown").upper()
                    fname = doc.get("filename", "attached_file")
                    summary_text = f"Attached {modality} document '{fname}' (Status: {doc.get('status', 'READY')})."
                    
                    # Fetch Knowledge Objects for detailed structural summary
                    kos = db_manager.get_knowledge_objects_by_document(fid)
                    if kos:
                        obj_types = set(k.get("object_type", "") for k in kos if k.get("object_type"))
                        summary_text += f" Structural components: {', '.join(sorted(obj_types))} ({len(kos)} elements)."
                        
                        # Extract entities from attached document content
                        for k in kos:
                            if k.get("content"):
                                extracted_query_entities.extend(extractor.extract_entities(k["content"]))
                                
                    input_summaries.append(summary_text)
                except Exception as e:
                    logger.warning(f"User {user_context.username} unauthorized for input document {fid}: {e}")
                    
        overall_input_summary = " ".join(input_summaries) if input_summaries else "Query referencing global index."
        t_entity = time.perf_counter() - t_entity_start
        
        # 2. Vector Semantic Retrieval (scoped when file_ids provided, global otherwise)
        t_embed_start = time.perf_counter()
        query_vector = LocalEmbeddingsCalculator.calculate_query_embedding(query)
        t_embed = time.perf_counter() - t_embed_start

        t_vector_start = time.perf_counter()
        raw_vector_matches = VectorDatabaseManager.semantic_query(
            "document_chunks",
            query_vector,
            query,
            limit * 4,
            filter_document_ids=file_ids if file_ids else None
        )
        t_vector = time.perf_counter() - t_vector_start
        
        # Pre-LLM RBAC Filter for Vector Matches
        authorized_vector_matches = []
        for match in raw_vector_matches:
            doc_id = match.get("metadata", {}).get("document_id")
            doc = db_manager.get_image(doc_id) if doc_id else None
            doc_class = doc.get("classification", "PUBLIC") if doc else "PUBLIC"
            try:
                authorize_document_classification(user_context, doc_class)
                authorized_vector_matches.append(match)
            except Exception:
                continue
                
        # 3. Bounded Graph Traversal & Expansion
        graph_expanded_nodes = []
        relationships_list = []
        
        t_graph_start = time.perf_counter()
        if use_graph_expansion and authorized_vector_matches:
            for vm in authorized_vector_matches[:3]:
                chunk_id = vm.get("chunk_id")
                if chunk_id:
                    neighbors = GraphReasoningEngine.find_neighbors(chunk_id, depth=1)
                    for n in neighbors:
                        n_doc_id = n.get("document_id")
                        # If query is scoped to specific documents, restrict graph traversal to those documents
                        if file_ids and n_doc_id and n_doc_id not in file_ids:
                            continue
                        n_doc_class = "PUBLIC"
                        if n_doc_id:
                            nd = db_manager.get_image(n_doc_id)
                            if nd:
                                n_doc_class = nd.get("classification", "PUBLIC")
                        try:
                            authorize_document_classification(user_context, n_doc_class)
                            graph_expanded_nodes.append(n)
                            
                            # Record graph relationship
                            rel_type = n.get("relationship_type", "CONNECTED_TO")
                            source_name = vm.get("metadata", {}).get("source_file", chunk_id)
                            target_name = n.get("content", n["id"])[:40]
                            relationships_list.append({
                                "source_name": source_name,
                                "relationship": rel_type,
                                "target_name": target_name,
                                "confidence": 0.9
                            })
                        except Exception:
                            continue
        t_graph = time.perf_counter() - t_graph_start
                            
        # 4. Related Knowledge Discovery (Documents, Images, Entities)
        # When querying the global corpus (not file_ids), discover related documents and images across authorized candidates.
        # When scoped to specific file_ids, the attached files are already represented in input_objects / input_summary;
        # external unattached documents are not pulled into related_documents.
        seen_doc_ids = set(d["id"] for d in input_docs)
        related_documents = []
        related_images = []
        
        if not file_ids:
            all_candidate_chunks = authorized_vector_matches + graph_expanded_nodes
            for candidate in all_candidate_chunks:
                doc_id = candidate.get("metadata", {}).get("document_id") or candidate.get("document_id")
                if not doc_id or doc_id in seen_doc_ids:
                    continue
                    
                doc_rec = db_manager.get_image(doc_id)
                if not doc_rec:
                    continue
                    
                seen_doc_ids.add(doc_id)
                modality = doc_rec.get("modality", "unknown")
                fname = doc_rec.get("filename", "unknown")
                classification = doc_rec.get("classification", "PUBLIC")
                
                asset_obj = {
                    "document_id": doc_id,
                    "filename": fname,
                    "modality": modality,
                    "classification": classification,
                    "relevance_score": round(candidate.get("score", 0.85), 2),
                    "page_number": candidate.get("metadata", {}).get("page_number", 1)
                }
                
                if modality in ["image", "png", "jpg", "jpeg"]:
                    asset_obj["thumbnail_url"] = f"/api/images/{doc_id}/raw"
                    related_images.append(asset_obj)
                else:
                    related_documents.append(asset_obj)
                
        # Consolidate Related Entities
        unique_entities = {}
        for ent in extracted_query_entities:
            ename = ent.get("value")
            etype = ent.get("type", "CONCEPT")
            if ename and ename not in unique_entities:
                unique_entities[ename] = {
                    "name": ename,
                    "entity_type": etype,
                    "mention_count": 1,
                    "source_documents": [d.get("filename") for d in input_docs if d.get("filename")]
                }
            elif ename in unique_entities:
                unique_entities[ename]["mention_count"] += 1

        related_entities = list(unique_entities.values())[:10]
        
        # 5. Deterministic RAG Execution & Answer Generation
        pipeline = ModularMultiAgentPipeline()
        rag_result = pipeline.execute_rag(
            query=query,
            user_role=user_context.role,
            history=history or [],
            limit=limit,
            file_ids=file_ids
        )
        
        citations = rag_result.get("citations", [])
        answer_stream = rag_result.get("answer_stream")
        
        # 6. Evidence Confidence Calculation
        confidence = EvidenceScorer.calculate_confidence(citations)
        
        t_total_prep = time.perf_counter() - t_pipeline_start
        timing_breakdown = {
            "entity_extraction_ms": round(t_entity * 1000, 1),
            "embedding_ms": round(t_embed * 1000, 1),
            "vector_retrieval_ms": round(t_vector * 1000, 1),
            "graph_traversal_ms": round(t_graph * 1000, 1),
            "pipeline_ms": rag_result.get("timing", {}).get("pipeline_prep_ms", 0.0),
            "total_prep_ms": round(t_total_prep * 1000, 1),
            "agent_details": rag_result.get("timing", {})
        }
        logger.info(f"[{trace_id}] Query pipeline prep completed in {t_total_prep:.3f}s. Breakdown: {timing_breakdown}")

        return {
            "trace_id": trace_id,
            "query": query,
            "input_summary": overall_input_summary,
            "answer_stream": answer_stream,
            "evidence_confidence": confidence,
            "citations": citations,
            "related_documents": related_documents[:6],
            "related_images": related_images[:6],
            "related_entities": related_entities,
            "relationships": relationships_list[:6],
            "input_objects": [
                {"document_id": d["id"], "filename": d["filename"], "modality": d.get("modality", "unknown")}
                for d in input_docs
            ],
            "timing_breakdown": timing_breakdown
        }
