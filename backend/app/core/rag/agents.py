import uuid
import time
import json
import logging
from typing import List, Dict, Any, Optional, Iterator
from app.core.vectordb import VectorDatabaseManager
from app.core.embeddings import LocalEmbeddingsCalculator
from app.core.graph.reasoning import GraphReasoningEngine
from app.core.rag.scoring import EvidenceScorer
from app.core.llm_provider import LLMProviderFactory
from app.core.security import authorize_document_classification, UserContext
from app.models.database import db_manager

logger = logging.getLogger(__name__)

class AgentContext:
    def __init__(self, user_role: str = "SYSTEM_ADMIN", timeout_seconds: float = 30.0):
        self.trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        self.user_role = user_role
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()

    def check_timeout(self):
        if time.time() - self.start_time > self.timeout_seconds:
            raise TimeoutError(f"Agent Pipeline execution exceeded timeout of {self.timeout_seconds}s")


class QueryPlanner:
    def run(self, query: str, context: AgentContext) -> Dict[str, Any]:
        context.check_timeout()
        keywords = [w.strip() for w in query.split() if len(w.strip()) > 3]
        return {
            "query": query,
            "sub_queries": [query] + keywords[:2],
            "use_graph": True,
            "trace_id": context.trace_id
        }


class RetrievalAgent:
    def run(self, plan: Dict[str, Any], context: AgentContext, limit: int = 5, file_ids: List[str] = None) -> List[Dict[str, Any]]:
        context.check_timeout()
        matches = []
        for q in plan["sub_queries"]:
            q_vector = LocalEmbeddingsCalculator.calculate_query_embedding(q)
            res = VectorDatabaseManager.semantic_query(
                "document_chunks",
                q_vector,
                q,
                limit=limit,
                filter_document_ids=file_ids if file_ids else None
            )
            matches.extend(res)
        # Deduplicate by ID and text content
        seen = set()
        seen_texts = set()
        unique = []
        
        # Inject attached files explicitly first
        if file_ids:
            from app.models.database import db_manager
            for fid in file_ids:
                kos = db_manager.get_knowledge_objects_by_document(fid)
                doc_chunk_count = 0
                for ko in kos:
                    if doc_chunk_count >= 10:
                        break # Limit to 10 most critical chunks per document to prevent massive LLM loading times
                    content = ko.get("content", "").strip()
                    if content:
                        ko_id = ko.get("id", "")
                        norm_text = content.lower()
                        if ko_id and ko_id not in seen and norm_text not in seen_texts:
                            seen.add(ko_id)
                            seen_texts.add(norm_text)
                            doc_chunk_count += 1
                            doc_rec = db_manager.get_image(fid)
                            meta_dict = json.loads(ko["metadata_json"]) if ko.get("metadata_json") else {}
                            unique.append({
                                "chunk_id": ko_id,
                                "text": content,
                                "score": 1.0,  # Max score to guarantee it stays in top evidence
                                "metadata": {
                                    "document_id": fid,
                                    "source_file": doc_rec.get("filename", "attached_file") if doc_rec else "attached_file",
                                    "page_number": ko.get("page_number", 1),
                                    "modality": doc_rec.get("modality", "document") if doc_rec else "document",
                                    "timestamp_str": meta_dict.get("timestamp_str"),
                                    "start_time": meta_dict.get("start_time"),
                                    "end_time": meta_dict.get("end_time")
                                }
                            })
                            
            # When file_ids is provided, query is strictly scoped to attached files!
            for m in matches:
                m_doc_id = m.get("metadata", {}).get("document_id")
                norm_text = m.get("text", "").strip().lower()
                if m_doc_id in file_ids and m["chunk_id"] not in seen and norm_text not in seen_texts:
                    seen.add(m["chunk_id"])
                    seen_texts.add(norm_text)
                    unique.append(m)
            return unique[:limit + 5]
                            
        for m in matches:
            norm_text = m.get("text", "").strip().lower()
            if m["chunk_id"] not in seen and norm_text not in seen_texts:
                seen.add(m["chunk_id"])
                seen_texts.add(norm_text)
                unique.append(m)
        return unique[:limit + (len(unique) if file_ids else 0)]


class GraphAgent:
    def run(self, matches: List[Dict[str, Any]], context: AgentContext, file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        context.check_timeout()
        graph_expanded = []
        seen = set()
        for m in matches:
            target_ids = []
            if m.get("metadata", {}).get("knowledge_object_id"):
                target_ids.append(m["metadata"]["knowledge_object_id"])
            chunk_id = m.get("chunk_id", "")
            if chunk_id:
                target_ids.append(chunk_id)
                if "_chunk_" in chunk_id:
                    target_ids.append(chunk_id.rsplit("_chunk_", 1)[0])
                    
            for tid in target_ids:
                try:
                    neighbors = GraphReasoningEngine.find_neighbors(tid, depth=1)
                    for n in neighbors:
                        # If file_ids is specified, do not traverse into external documents
                        n_doc_id = n.get("document_id")
                        if file_ids and n_doc_id and n_doc_id not in file_ids:
                            continue
                        nid = n.get("id") or n.get("knowledge_object_id")
                        if nid and nid not in seen:
                            seen.add(nid)
                            n["_expanded_from"] = m.get("metadata", {}).get("source_file", "document")
                            graph_expanded.append(n)
                except Exception as e:
                    logger.warning(f"GraphAgent expansion failed for node {tid}: {e}")
        return graph_expanded


class EvidenceAgent:
    def run(self, vector_matches: List[Dict[str, Any]], graph_nodes: List[Dict[str, Any]], context: AgentContext) -> List[Dict[str, Any]]:
        context.check_timeout()
        # RBAC Filter vector matches
        user_ctx = UserContext(id="system", username="system", role=context.user_role)
        authorized = []
        seen_ids = set()

        for vm in vector_matches:
            doc_id = vm.get("metadata", {}).get("document_id")
            doc = db_manager.get_image(doc_id) if doc_id else None
            classification = doc.get("classification", "PUBLIC") if doc else "PUBLIC"
            try:
                authorize_document_classification(user_ctx, classification)
                cid = vm.get("chunk_id")
                if cid:
                    seen_ids.add(cid)
                authorized.append(vm)
            except Exception:
                continue

        # RBAC Filter and incorporate Graph-expanded knowledge nodes
        for gn in graph_nodes:
            gn_id = gn.get("id") or gn.get("knowledge_object_id")
            if not gn_id or gn_id in seen_ids:
                continue
            doc_id = gn.get("document_id")
            doc = db_manager.get_image(doc_id) if doc_id else None
            classification = doc.get("classification", "PUBLIC") if doc else "PUBLIC"
            try:
                authorize_document_classification(user_ctx, classification)
            except Exception:
                continue

            content = gn.get("content", "").strip()
            if not content:
                continue

            seen_ids.add(gn_id)
            source_file = doc.get("filename", "document") if doc else gn.get("_expanded_from", "Knowledge Graph")
            rel_type = gn.get("relationship_type", "CONNECTED_TO")
            obj_type = gn.get("object_type", "entity")
            score = float(gn.get("confidence", 0.88))

            authorized.append({
                "chunk_id": gn_id,
                "text": f"[{rel_type} -> {obj_type.upper()}] {content}",
                "score": score,
                "metadata": {
                    "document_id": doc_id,
                    "source_file": source_file,
                    "page_number": gn.get("page_number", 1),
                    "bounding_box": gn.get("bounding_box", [0, 0, 1000, 1000]),
                    "source_type": "graph_relationship",
                    "relationship_type": rel_type,
                    "object_type": obj_type
                }
            })

        # Score & rank using EvidenceScorer
        ranked = EvidenceScorer.rank_matches(authorized)
        return ranked


class AnswerAgent:
    def run(self, query: str, evidence: List[Dict[str, Any]], history: List[Dict[str, str]], context: AgentContext) -> Iterator[str]:
        context.check_timeout()
        provider = LLMProviderFactory.get_provider()

        if not evidence:
            yield "I could not find any relevant authorized context in the uploaded documents to answer your question."
            return

        context_blocks = []
        for m in evidence:
            meta = m.get("metadata", {})
            fname = meta.get("source_file", "document")
            source_type = meta.get("source_type", "vector")
            time_info = ""
            if meta.get("timestamp_str"):
                time_info = f" [{meta['timestamp_str']}]"
            elif "start_time" in meta and "end_time" in meta:
                time_info = f" [{meta['start_time']}s - {meta['end_time']}s]"
            
            if source_type == "graph_relationship":
                rel = meta.get("relationship_type", "CONNECTED_TO")
                context_blocks.append(f"[Knowledge Graph Relation: {rel} ({fname}{time_info})]\n{m['text']}")
            else:
                context_blocks.append(f"[Filename: {fname}{time_info}]\n{m['text']}")

        context_str = "\n\n".join(context_blocks)
        system_prompt = (
            "You are a secure, local document intelligence AI. "
            "Answer the user's question based ONLY on the provided context (including any Knowledge Graph relations). "
            "Always refer to the documents by their actual filenames and mention relevant structural connections."
        )

        prompt = f"Document Context:\n{context_str}\n\nUser: {query}\n\nAssistant:"
        yield from provider.generate_stream(prompt, system_prompt)


class CitationAgent:
    def run(self, evidence: List[Dict[str, Any]], context: Optional[AgentContext] = None) -> List[Dict[str, Any]]:
        if context:
            context.check_timeout()
        citations = []
        for item in evidence:
            meta = item.get("metadata", {})
            source_file = meta.get("source_file", "unknown")
            modality = meta.get("modality", "document").lower()
            
            # Formulate modality-specific unified evidence reference
            evidence_ref = f"{source_file}"
            if "start_sec" in meta and "end_sec" in meta:
                evidence_ref = f"{source_file}:{meta['start_sec']}s-{meta['end_sec']}s"
            elif "start_time" in meta or "timestamp_str" in meta or modality in ["audio", "video"]:
                t_str = meta.get("timestamp_str") or f"{meta.get('start_time', 0.0)}s - {meta.get('end_time', 0.0)}s"
                evidence_ref = f"{source_file} [{t_str}]"
            elif meta.get("sheet_name") and ("row_index" in meta or "row_number" in meta):
                r = meta.get("row_index", meta.get("row_number"))
                evidence_ref = f"{source_file}#{meta['sheet_name']}:R{r}"
            elif meta.get("slide_number"):
                evidence_ref = f"{source_file} [Slide {meta['slide_number']}]"
            elif meta.get("sheet_name"):
                evidence_ref = f"{source_file} [Sheet: {meta['sheet_name']}]"
            elif meta.get("row_number"):
                evidence_ref = f"{source_file} [Row: {meta['row_number']}]"
            elif meta.get("page_number"):
                evidence_ref = f"{source_file} [Page {meta['page_number']}]"

            citations.append({
                "chunk_id": item.get("chunk_id") or item.get("id"),
                "text": item.get("text", "")[:150],
                "score": item.get("score", 0.0),
                "evidence_ref": evidence_ref,
                "metadata": {
                    "source_file": source_file,
                    "document_id": meta.get("document_id"),
                    "page_number": meta.get("page_number", 1),
                    "bounding_box": meta.get("bounding_box", [0, 0, 1000, 1000]),
                    "source_type": meta.get("source_type", "vector"),
                    "relationship_type": meta.get("relationship_type", None),
                    "modality": modality,
                    "start_time": meta.get("start_time"),
                    "end_time": meta.get("end_time"),
                    "start_sec": meta.get("start_sec"),
                    "end_sec": meta.get("end_sec"),
                    "timestamp_str": meta.get("timestamp_str"),
                    "evidence_ref": evidence_ref
                }
            })
        return citations

    def format_citations(self, evidence: List[Dict[str, Any]], context: Optional[AgentContext] = None) -> List[Any]:
        class CitationItem:
            def __init__(self, citation_number, source_file, evidence_ref, raw):
                self.citation_number = citation_number
                self.source_file = source_file
                self.evidence_ref = evidence_ref
                self.raw = raw
            def __repr__(self):
                return f"CitationItem([{self.citation_number}] {self.source_file}: {self.evidence_ref})"

        raw_citations = self.run(evidence, context)
        return [
            CitationItem(idx, c["metadata"].get("source_file", "source"), c.get("evidence_ref"), c)
            for idx, c in enumerate(raw_citations, 1)
        ]



class ModularMultiAgentPipeline:
    """Orchestrates single-pass 6-stage deterministic agent execution."""

    def __init__(self):
        self.planner = QueryPlanner()
        self.retrieval = RetrievalAgent()
        self.graph = GraphAgent()
        self.evidence = EvidenceAgent()
        self.answer = AnswerAgent()
        self.citation = CitationAgent()

    def execute_rag(self, query: str, user_role: str = "SYSTEM_ADMIN", history: List[Dict[str, str]] = None, limit: int = 5, file_ids: List[str] = None):
        if history is None:
            history = []
        ctx = AgentContext(user_role=user_role)
        
        t0 = time.perf_counter()
        plan = self.planner.run(query, ctx)
        t_plan = time.perf_counter() - t0

        t1 = time.perf_counter()
        vector_matches = self.retrieval.run(plan, ctx, limit=limit, file_ids=file_ids)
        t_retrieval = time.perf_counter() - t1

        t2 = time.perf_counter()
        graph_nodes = self.graph.run(vector_matches, ctx, file_ids=file_ids)
        t_graph = time.perf_counter() - t2

        t3 = time.perf_counter()
        evidence = self.evidence.run(vector_matches, graph_nodes, ctx)
        t_evidence = time.perf_counter() - t3

        t4 = time.perf_counter()
        citations = self.citation.run(evidence, ctx)
        t_citation = time.perf_counter() - t4

        t5 = time.perf_counter()
        answer_stream = self.answer.run(query, evidence, history, ctx)
        t_answer = time.perf_counter() - t5

        return {
            "trace_id": ctx.trace_id,
            "citations": citations,
            "answer_stream": answer_stream,
            "timing": {
                "planner_ms": round(t_plan * 1000, 1),
                "retrieval_ms": round(t_retrieval * 1000, 1),
                "graph_ms": round(t_graph * 1000, 1),
                "evidence_ms": round(t_evidence * 1000, 1),
                "citation_ms": round(t_citation * 1000, 1),
                "pipeline_prep_ms": round((time.perf_counter() - t0) * 1000, 1)
            }
        }

QueryPlannerAgent = QueryPlanner
