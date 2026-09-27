import logging
import numpy as np
import cv2
from typing import Dict, Any, List

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from app.core.ingestion.adapters.pdf_engines import BasePDFEngine
from app.core.ingestion.detector import CorruptedFileError

logger = logging.getLogger(__name__)

class PyMuPDFEngine(BasePDFEngine):
    """
    Primary PDF Engine utilizing PyMuPDF (AGPL).
    Provides native text extraction, image extraction, and fast page rendering.
    """
    
    def __init__(self):
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) is not installed. Run 'pip install pymupdf'.")
            
    def open_document(self, file_bytes: bytes) -> Any:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if doc.is_encrypted:
                # Attempt to open with empty password, some PDFs just use encryption for permissions
                success = doc.authenticate("")
                if not success:
                    raise ValueError("Password-protected PDF not currently supported.")
            return doc
        except Exception as e:
            raise CorruptedFileError(f"Failed to open PDF: {str(e)}")

    def close_document(self, doc_handle: Any):
        if doc_handle:
            doc_handle.close()

    def get_metadata(self, doc_handle: Any) -> Dict[str, Any]:
        meta = doc_handle.metadata
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "keywords": meta.get("keywords", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "creation_date": meta.get("creationDate", ""),
            "mod_date": meta.get("modDate", ""),
            "is_encrypted": doc_handle.is_encrypted,
            "page_count": len(doc_handle)
        }

    def get_page_count(self, doc_handle: Any) -> int:
        return len(doc_handle)

    def extract_page_data(self, doc_handle: Any, page_num: int, render_images: bool = False) -> Dict[str, Any]:
        page = doc_handle.load_page(page_num)
        
        # 1. Native Text
        text_content = page.get_text("text")
        text_blocks = [text_content.strip()] if text_content.strip() else []
        
        extracted_images = []
        
        # 2. Render whole page if requested (e.g. for OCR)
        if render_images:
            pix = page.get_pixmap()
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            # Convert RGB to BGR for OpenCV
            if pix.n == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)
                
            extracted_images.append(img_array)
        else:
            # 3. Native Embedded Image Extraction
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc_handle.extract_image(xref)
                if base_image:
                    image_bytes = base_image["image"]
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is not None:
                        extracted_images.append(img)
                        
        return {
            "text_blocks": text_blocks,
            "images": extracted_images,
            "tables": [] # Handled by TableExtractor abstraction
        }
