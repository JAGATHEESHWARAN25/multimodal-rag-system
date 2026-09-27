from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BasePDFEngine(ABC):
    """
    Abstract interface for PDF processing engines (PyMuPDF, pdfplumber, etc.).
    Decouples the PDF Adapter from specific PDF parsing libraries.
    """
    
    @abstractmethod
    def open_document(self, file_bytes: bytes) -> Any:
        """Opens and returns the document object handle."""
        pass
        
    @abstractmethod
    def close_document(self, doc_handle: Any):
        """Releases the document handle."""
        pass
        
    @abstractmethod
    def get_metadata(self, doc_handle: Any) -> Dict[str, Any]:
        """Extracts native metadata like title, author, encryption status."""
        pass
        
    @abstractmethod
    def get_page_count(self, doc_handle: Any) -> int:
        """Returns the total number of pages."""
        pass
        
    @abstractmethod
    def extract_page_data(self, doc_handle: Any, page_num: int, render_images: bool = False) -> Dict[str, Any]:
        """
        Extracts all data for a specific page.
        Returns a dict containing:
        - text_blocks: List of strings
        - images: List of numpy arrays
        - tables: List of dictionaries (optional fallback if engine supports it)
        If render_images is True, the whole page should be rendered as a numpy array.
        """
        pass
