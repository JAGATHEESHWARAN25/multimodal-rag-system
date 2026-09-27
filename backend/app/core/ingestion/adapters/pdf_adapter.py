import hashlib
import uuid
import logging
import cv2
from typing import Dict, Any, Generator, Union

from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.resource_manager import resource_manager
from app.core.ingestion.adapters.pdf_engines import BasePDFEngine
from app.core.ingestion.adapters.pymupdf_engine import PyMuPDFEngine
from app.core.ingestion.adapters.table_extractors import NativeTableExtractor

logger = logging.getLogger(__name__)

class PDFAdapter(BaseAdapter):
    """
    Adapter for processing PDF files.
    Utilizes an abstracted PDF engine (PyMuPDF by default) and supports incremental batch streaming.
    """
    
    def __init__(self, engine: BasePDFEngine = None):
        super().__init__()
        self.modality = "pdf"
        self.engine = engine or PyMuPDFEngine()
        self.table_extractor = NativeTableExtractor()

    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> Generator[CommonDocumentObject, None, None]:
        """Parses PDF bytes into CommonDocumentObjects using batched streaming."""
        
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()
        
        doc_handle = self.engine.open_document(file_bytes)
        
        try:
            native_metadata = self.engine.get_metadata(doc_handle)
            page_count = self.engine.get_page_count(doc_handle)
            
            # Combine provided metadata with native PDF metadata
            combined_metadata = {**file_metadata, **native_metadata}
            
            # Streaming Strategy: Batch calculation
            batch_size = resource_manager.get_batch_size()
            logger.info(f"Processing PDF {file_metadata['filename']} with batch size {batch_size}")
            
            # Collect all pages for document
            all_pages = []
            all_images = []
            extracted_assets = []
            
            for page_num in range(page_count):
                # 1. Native Extraction Priority
                page_data = self.engine.extract_page_data(doc_handle, page_num, render_images=False)
                
                # Check for Scanned / Image-based pages: If text is absent or insufficient (< 25 chars)
                native_text_len = sum(len(tb.strip()) for tb in page_data.get("text_blocks", []))
                if native_text_len < 25:
                    try:
                        import numpy as np
                        from app.core.model_manager import model_manager
                        
                        # Render page pixmap with PyMuPDF
                        page_obj = doc_handle.load_page(page_num)
                        pix = page_obj.get_pixmap(dpi=150)
                        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                        if pix.n == 3:
                            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                        elif pix.n == 4:
                            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
                            
                        # Run OCR first to extract all visible text on the page
                        ocr_model = model_manager.get_model("ocr", "tesseract") or model_manager.get_model("ocr", "paddleocr")
                        if ocr_model:
                            ocr_res = ocr_model.predict(arr)
                            ocr_text = ocr_res.get("text", "").strip()
                            if ocr_text:
                                paras = [p.strip() for p in ocr_text.split("\n\n") if p.strip()]
                                page_data["text_blocks"].extend(paras if paras else [ocr_text])
                                logger.info(f"PDF page {page_num+1} scanned OCR extracted {len(ocr_text)} characters.")
                    except Exception as ocr_err:
                        logger.warning(f"Fallback OCR on PDF page {page_num+1} failed: {ocr_err}")
                
                # 2. Extract Tables
                tables = self.table_extractor.extract_tables(doc_handle, page_num)
                page_data["tables"] = tables
                
                # Keep visual assets available for VisionPipeline (limit to first 3 per page to conserve RAM)
                page_images = page_data.get("images", [])[:3]
                all_images.extend(page_images)
                
                all_pages.append({
                    "page_num": page_num,
                    "text_blocks": page_data["text_blocks"],
                    "tables": page_data["tables"],
                    "images": page_images
                })
                
            cdo = CommonDocumentObject(
                document_id=doc_id,
                fingerprint=sha256_hash,
                modality=self.modality,
                filename=file_metadata["filename"],
                mime_type=file_metadata["mime_type"],
                metadata=combined_metadata,
                source_information={
                    "adapter": "PDFAdapter", 
                    "engine": self.engine.__class__.__name__,
                    "page_count": page_count
                },
                pages=all_pages,
                images=all_images,
                extracted_assets=extracted_assets
            )
            
            self.emit_event("DocumentParsed", {"document_id": doc_id, "status": "Success", "modality": self.modality})
            yield cdo
                    
        finally:
            self.engine.close_document(doc_handle)
