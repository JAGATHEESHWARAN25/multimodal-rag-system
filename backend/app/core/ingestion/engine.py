from typing import Union, Generator, Iterator, Any
import logging

from app.core.ingestion.detector import FileDetector
from app.core.ingestion.adapters.manager import AdapterManager
from app.models.schema import CommonDocumentObject
from app.core.events import event_bus

logger = logging.getLogger(__name__)

class IngestionEngine:
    """
    The Unified Ingestion Engine.
    Single entry point for all documents. Validates files, resolves adapters,
    and returns a CommonDocumentObject (or a stream of them).
    """

    @classmethod
    def ingest_file(cls, file_bytes: bytes, original_filename: str) -> Union[CommonDocumentObject, Generator[CommonDocumentObject, None, None]]:
        """
        Main pipeline ingestion method.
        
        Lifecycle:
        1. File Validation (Detector)
        2. Adapter Resolution (Manager)
        3. Parsing & Normalization (Adapter) -> CommonDocumentObject
        """
        logger.info(f"Ingesting file: {original_filename}")
        
        # 1. Detection & Validation
        file_metadata = FileDetector.analyze_file(file_bytes, original_filename)
        mime_type = file_metadata["mime_type"]
        
        # 2. Adapter Resolution
        adapter = AdapterManager.get_adapter(mime_type)
        
        event_bus.emit("AdapterSelected", {
            "filename": original_filename,
            "mime_type": mime_type,
            "adapter": adapter.__class__.__name__
        })
        
        # 3. Parsing
        result = adapter.parse(file_bytes, file_metadata)
        
        if isinstance(result, Generator):
            # If the adapter is streaming (e.g., large PDF), we wrap the generator to emit events per chunk/page
            def stream_wrapper():
                for cdo in result:
                    event_bus.emit("CommonDocumentObjectCreated", {
                        "document_id": cdo.document_id, 
                        "filename": cdo.filename,
                        "streaming": True
                    })
                    yield cdo
            return stream_wrapper()
        else:
            # Single object returned
            event_bus.emit("CommonDocumentObjectCreated", {
                "document_id": result.document_id,
                "filename": result.filename,
                "streaming": False
            })
            return result
