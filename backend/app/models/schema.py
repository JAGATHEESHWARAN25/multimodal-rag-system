from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

class ProcessingMetadata(BaseModel):
    profile_used: str = ""
    cost_estimation: Dict[str, Any] = Field(default_factory=dict)
    enhancement_trace: List[str] = Field(default_factory=list)
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)
    ocr_performance: Dict[str, Any] = Field(default_factory=dict)

class RelationshipEdge(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str = Field(..., description="e.g., 'CHILD_OF', 'CONNECTED_TO', 'REFERENCES'")
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeObject(BaseModel):
    knowledge_object_id: str
    parent_document_id: str = ""
    parent_object_id: Optional[str] = None
    page_number: Optional[int] = None
    block_type: str = Field(..., description="e.g., 'document', 'page', 'table', 'paragraph', 'heading', 'figure', 'node'")
    content: str = ""
    caption: Optional[str] = None
    bounding_box: Optional[List[Union[float, int]]] = None
    engine_used: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UniversalKnowledgeSchema(BaseModel):
    schema_version: str = "1.0"
    document_id: str
    sha256_hash: str
    source_file: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_metadata: ProcessingMetadata = Field(default_factory=ProcessingMetadata)
    global_summary: str = ""
    semantic_blocks: List[KnowledgeObject] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list) # Placeholder for future
    relationships: List[RelationshipEdge] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list) # Placeholder for future

class CommonDocumentObject(BaseModel):
    """
    Standardized input format for the Phase 1.5+ Pipeline.
    Adapters convert files into this object. Supports streaming via iterators for large docs.
    """
    schema_version: str = "2.0"
    document_id: str
    fingerprint: str
    modality: str = Field(..., description="e.g., 'image', 'pdf', 'docx'")
    filename: str
    mime_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_information: Dict[str, Any] = Field(default_factory=dict)
    
    pages: List[Any] = Field(default_factory=list) 
    text_blocks: List[str] = Field(default_factory=list) 
    images: List[Any] = Field(default_factory=list) 
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    diagrams: List[Dict[str, Any]] = Field(default_factory=list)
    attachments: List[Any] = Field(default_factory=list) 
    audio_streams: List[Any] = Field(default_factory=list)
    video_streams: List[Any] = Field(default_factory=list)
    extracted_assets: List[str] = Field(default_factory=list) # Paths to cached assets
    
    processing_profile: str = "Balanced"
