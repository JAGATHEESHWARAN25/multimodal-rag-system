import logging
from typing import List, Dict, Any
from app.models.database import db_manager
from app.core.llm import LocalLLMConnector

logger = logging.getLogger(__name__)

import sqlite3

class DocumentSummarizer:
    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 4000) -> List[str]:
        # Naive chunking for very large documents
        words = text.split()
        chunks = []
        current = []
        current_len = 0
        for word in words:
            if current_len + len(word) > chunk_size:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            current.append(word)
            current_len += len(word) + 1
        if current:
            chunks.append(" ".join(current))
        return chunks

    @staticmethod
    def _extract_text_from_document(document_id: str) -> str:
        # Fetch knowledge objects for this document to build a complete text including tables and image OCR
        with db_manager._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT object_type, content FROM knowledge_objects WHERE document_id = ? ORDER BY created_at ASC",
                (document_id,)
            )
            rows = cursor.fetchall()
            
            # Check if this document has audio segments
            has_audio = any((r["object_type"] or "").lower() == "audio_segment" for r in rows)
            
            blocks = []
            for row in rows:
                if not row["content"]:
                    continue
                obj_type = (row["object_type"] or "TEXT").upper()
                content = row["content"]
                
                if has_audio:
                    if obj_type == "AUDIO_SEGMENT":
                        blocks.append(content)
                    continue
                    
                if obj_type in ("PAGE", "ENTITY"):
                    continue
                elif obj_type == "TABLE":
                    blocks.append(f"[TABLE DATA]\n{content}")
                elif obj_type == "IMAGE":
                    blocks.append(f"[IMAGE OCR EXTRACTED TEXT]\n{content}")
                else:
                    blocks.append(content)
                    
            return "\n\n".join(blocks)

    @classmethod
    def summarize_document(cls, document_id: str, force_refresh: bool = False) -> str:
        # Check SQLite cache first if not forced refresh
        if not force_refresh:
            cached_summary = db_manager.get_document_summary(document_id)
            if cached_summary:
                logger.info(f"Retrieved cached summary for document {document_id}")
                return cached_summary

        import sqlite3 # Lazy import if needed
        text = cls._extract_text_from_document(document_id)
        if not text:
            return "No readable content found in this document to summarize."
            
        system_prompt = (
            "You are an expert Intelligence Analyst. Summarize the provided document context into a structured report.\n"
            "Format your output exactly with these sections (using Markdown):\n"
            "## Executive Summary\n"
            "## Key Points\n"
            "## Important Entities\n"
            "## Dates\n"
            "## Risks / Issues\n"
            "## Action Items\n\n"
            "Do not include any other conversational filler."
        )
        
        chunks = cls._chunk_text(text)
        
        summary_result = ""
        if len(chunks) == 1:
            try:
                summary_result = LocalLLMConnector.generate_response(chunks[0], system_prompt=system_prompt)
            except Exception:
                summary_result = cls._mock_summarize(text)
        else:
            # Map-Reduce approach for multiple chunks
            partial_summaries = []
            for i, chunk in enumerate(chunks[:5]): # Limit to first 5 chunks to avoid massive LLM wait times
                try:
                    partial = LocalLLMConnector.generate_response(
                        f"Summarize part {i+1}:\n{chunk}", 
                        system_prompt="Extract key points from this section."
                    )
                    partial_summaries.append(partial)
                except Exception:
                    partial_summaries.append(f"[Mock Partial Summary {i+1}]")
            
            combined_text = "\n\n".join(partial_summaries)
            try:
                summary_result = LocalLLMConnector.generate_response(combined_text, system_prompt=system_prompt)
            except Exception:
                summary_result = cls._mock_summarize(combined_text)

        # Cache the generated summary in SQLite
        if summary_result and not summary_result.startswith("No readable content"):
            try:
                db_manager.save_document_summary(document_id, summary_result)
                logger.info(f"Persisted cached summary for document {document_id}")
            except Exception as e:
                logger.error(f"Failed to cache summary for document {document_id}: {e}")

        return summary_result
                
    @staticmethod
    def _mock_summarize(text: str) -> str:
        return (
            "## Executive Summary\n"
            "This is a mocked executive summary generated locally.\n\n"
            "## Key Points\n"
            "- Mock Point 1\n"
            "- Mock Point 2\n\n"
            "## Important Entities\n"
            "- Organization: Mock Org\n\n"
            "## Dates\n"
            "- None extracted\n\n"
            "## Risks / Issues\n"
            "- None identified\n\n"
            "## Action Items\n"
            "- None\n"
        )
