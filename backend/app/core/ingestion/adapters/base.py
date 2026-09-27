from abc import ABC, abstractmethod
from typing import Dict, Any, Generator, Union
from app.models.schema import CommonDocumentObject
from app.core.events import event_bus

class BaseAdapter(ABC):
    """
    Abstract Base Class for all Ingestion Adapters.
    Every adapter must implement the parse method which returns a CommonDocumentObject
    (or yields it for streaming large documents).
    """
    
    def __init__(self):
        self.modality = "unknown"

    @abstractmethod
    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> Union[CommonDocumentObject, Generator[CommonDocumentObject, None, None]]:
        """
        Parses the raw file bytes into a CommonDocumentObject.
        Adapters must only extract and normalize; they must NOT perform AI inference (OCR, VLM, embeddings).
        
        Args:
            file_bytes (bytes): The raw file content.
            file_metadata (dict): Metadata from the FileDetector (mime_type, filename, size_bytes).
            
        Returns:
            CommonDocumentObject or a Generator yielding CommonDocumentObject for streaming.
        """
        pass
        
    def emit_event(self, event_name: str, payload: Dict[str, Any]):
        """Helper to emit ingestion events."""
        event_bus.emit(event_name, payload)
