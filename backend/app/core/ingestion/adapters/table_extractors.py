from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseTableExtractor(ABC):
    """
    Abstract interface for table extraction engines.
    Decouples the PDF Adapter from specific table parsers like Camelot, pdfplumber, or native fallback.
    """
    
    @abstractmethod
    def extract_tables(self, doc_handle: Any, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract tables from the given page.
        Returns a list of table data structures.
        """
        pass

class NativeTableExtractor(BaseTableExtractor):
    """
    Native structural table extractor using PyMuPDF page.find_tables().
    Extracts headers, rows, bounding box coordinates, and markdown table strings.
    """
    def extract_tables(self, doc_handle: Any, page_num: int) -> List[Dict[str, Any]]:
        tables = []
        try:
            if hasattr(doc_handle, "__getitem__"):
                page = doc_handle[page_num]
            elif hasattr(doc_handle, "load_page"):
                page = doc_handle.load_page(page_num)
            else:
                return []

            if hasattr(page, "find_tables"):
                tab_finder = page.find_tables()
                if tab_finder and getattr(tab_finder, "tables", None):
                    for tab in tab_finder.tables:
                        df = tab.extract()
                        if not df or len(df) == 0:
                            continue
                        headers = [str(c or "").strip() for c in df[0]]
                        rows = [[str(c or "").strip() for c in r] for r in df[1:]] if len(df) > 1 else []
                        bbox = [float(x) for x in getattr(tab, "bbox", [0, 0, 1000, 1000])]
                        
                        markdown_lines = []
                        if headers:
                            markdown_lines.append("| " + " | ".join(headers) + " |")
                            markdown_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                        for row in rows:
                            markdown_lines.append("| " + " | ".join(row) + " |")

                        tables.append({
                            "type": "table",
                            "headers": headers,
                            "rows": rows,
                            "markdown": "\n".join(markdown_lines),
                            "bounding_box": bbox,
                            "confidence": 0.95
                        })
        except Exception:
            pass
        return tables
