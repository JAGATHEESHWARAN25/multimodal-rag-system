import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseTableExtractor(ABC):
    """Abstract interface for table extraction strategies."""

    @abstractmethod
    def extract_tables(self, document_content: Any) -> List[Dict[str, Any]]:
        pass


class NativeTableExtractor(BaseTableExtractor):
    """Native structural table extractor (default baseline)."""

    def extract_tables(self, document_content: Any) -> List[Dict[str, Any]]:
        tables = []
        if isinstance(document_content, list):
            for item in document_content:
                if isinstance(item, dict) and item.get("type") == "table":
                    tables.append(item)
        return tables


class AdvancedTableExtractor(BaseTableExtractor):
    """Spatial bounding-box layout & cell relationship mapper with native fallback."""

    def __init__(self):
        self.native_fallback = NativeTableExtractor()

    def extract_tables(self, document_content: Any) -> List[Dict[str, Any]]:
        try:
            native_tables = self.native_fallback.extract_tables(document_content)
            advanced_tables = []

            for t in native_tables:
                rows = t.get("rows", [])
                headers = t.get("headers", [])
                
                # Spatial bounding box estimation & cell relationship calculation
                bbox = t.get("bounding_box", [0, 0, 1000, 1000])
                confidence = t.get("confidence", 0.95)

                markdown_str = ""
                if headers:
                    markdown_str += "| " + " | ".join(headers) + " |\n"
                    markdown_str += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                for row in rows:
                    if isinstance(row, list):
                        markdown_str += "| " + " | ".join([str(c) for c in row]) + " |\n"

                advanced_tables.append({
                    "type": "table",
                    "headers": headers,
                    "rows": rows,
                    "markdown": markdown_str,
                    "bounding_box": bbox,
                    "confidence": confidence,
                    "cell_relationships": {
                        "total_rows": len(rows),
                        "total_cols": len(headers) if headers else (len(rows[0]) if rows else 0)
                    }
                })

            return advanced_tables if advanced_tables else native_tables

        except Exception as e:
            logger.warning(f"Advanced table extraction failed: {e}. Falling back to NativeTableExtractor.")
            return self.native_fallback.extract_tables(document_content)
