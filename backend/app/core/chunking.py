import logging
from typing import List, Dict, Any
from app.models.schema import UniversalKnowledgeSchema, KnowledgeObject
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

class SemanticChunker:
    """
    Chunks text strictly within the boundaries of Semantic Blocks (Knowledge Objects).
    Never crosses table/paragraph boundaries.
    """
    
    @staticmethod
    def chunk_schema(schema: UniversalKnowledgeSchema, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict[str, Any]]:
        chunks = []
        
        for block in schema.semantic_blocks:
            text = block.content
            if not text:
                continue
                
            block_type = getattr(block, "block_type", "")
            if block_type not in ["paragraph", "heading", "text", "cell", "audio_segment", "video_segment", "page_summary"]:
                continue
                
            block_chunks = SemanticChunker._chunk_text(text, chunk_size, overlap)
            
            for idx, c_text in enumerate(block_chunks):
                chunk_id = f"{block.knowledge_object_id}_chunk_{idx}"
                
                metadata = {
                    "document_id": schema.document_id,
                    "sha256_hash": schema.sha256_hash,
                    "knowledge_object_id": block.knowledge_object_id,
                    "block_type": block.block_type,
                    "source_file": schema.source_file,
                    "schema_version": schema.schema_version,
                    "chunk_index": idx
                }
                if block.metadata:
                    for k, v in block.metadata.items():
                        if isinstance(v, (str, int, float, bool)):
                            metadata[k] = v
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": c_text,
                    "metadata": metadata
                })
                
        return chunks

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Simple character-based chunking with overlap."""
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to snap to the nearest space backwards to avoid splitting words
            if end < len(text) and text[end] != ' ':
                last_space = text.rfind(' ', start, end)
                if last_space != -1 and last_space > start:
                    end = last_space
                    
            chunks.append(text[start:end].strip())
            start = max(start + 1, end - overlap)
            
        return chunks
