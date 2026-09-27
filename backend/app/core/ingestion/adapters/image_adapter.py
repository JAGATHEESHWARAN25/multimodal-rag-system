from typing import Dict, Any, Generator, Union
import hashlib
import uuid
import numpy as np
import cv2
from datetime import datetime

from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.resource_manager import resource_manager

class ImageAdapter(BaseAdapter):
    """
    Adapter for processing image files (.png, .jpg, .webp).
    """
    
    def __init__(self):
        super().__init__()
        self.modality = "image"
        
    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> Union[CommonDocumentObject, Generator[CommonDocumentObject, None, None]]:
        """Parses image bytes into a CommonDocumentObject."""
        # 1. Generate core identities
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # 2. Extract specific image metadata (dimensions, channels)
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError(f"Failed to decode image bytes for {file_metadata.get('filename')}")
            
        h, w, c = img.shape
        
        extracted_metadata = {
            "original_filename": file_metadata["filename"],
            "image_width": w,
            "image_height": h,
            "channels": c,
            "creation_date": datetime.now().isoformat()
        }
        
        # 3. Handle Resource Strategy (Disk Cache vs Memory)
        # Even for images, if memory is very tight, we could write to disk.
        # But generally images are processed in-memory unless they are gigantic.
        should_stream = resource_manager.should_stream(len(file_bytes), estimated_expansion_factor=5)
        
        extracted_assets = []
        images_in_memory = [img]
        
        if should_stream:
            # Also write image to temporary disk cache
            asset_path = resource_manager.get_temp_asset_path(doc_id, file_metadata["filename"])
            cv2.imwrite(str(asset_path), img)
            extracted_assets.append(str(asset_path))
            
        # 4. Construct CommonDocumentObject
        cdo = CommonDocumentObject(
            document_id=doc_id,
            fingerprint=sha256_hash,
            modality=self.modality,
            filename=file_metadata["filename"],
            mime_type=file_metadata["mime_type"],
            metadata=extracted_metadata,
            source_information={"adapter": "ImageAdapter", "streaming_mode": should_stream},
            images=images_in_memory,
            extracted_assets=extracted_assets
        )
        
        self.emit_event("DocumentParsed", {"document_id": doc_id, "status": "Success", "modality": self.modality})
        
        return cdo
