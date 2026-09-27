import io
import logging
from typing import Dict, Any, Generator, Union, List
import docx
from docx.document import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from docx.opc.exceptions import PackageNotFoundError

from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.ingestion.detector import CorruptedFileError

logger = logging.getLogger(__name__)

def iter_block_items(parent):
    """
    Yield each paragraph and table child within *parent*, in document order.
    Each returned value is an instance of either Table or Paragraph.
    """
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    elif hasattr(parent, '_element'):
        # For _Header / _Footer
        parent_elm = parent._element
    else:
        raise ValueError("Unsupported parent type for block iteration")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

class DOCXAdapter(BaseAdapter):
    """
    Adapter for processing Microsoft Word (.docx) files.
    Preserves document ordering, formatting, headings, lists, and tables.
    Extracts embedded images.
    """
    
    def __init__(self):
        super().__init__()
        self.modality = "docx"
        
    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> Union[CommonDocumentObject, Generator[CommonDocumentObject, None, None]]:
        self.emit_event("AdapterParsingStarted", {"modality": self.modality, "filename": file_metadata.get("filename", "")})
        
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
        except PackageNotFoundError:
            raise CorruptedFileError("Invalid or corrupted DOCX file.")
        except Exception as e:
            raise CorruptedFileError(f"Failed to parse DOCX: {str(e)}")
            
        elements = []
        
        # 1. Process Sections (Headers/Footers)
        # To preserve section mapping, we'll track active section.
        # python-docx doesn't easily map body paragraphs to sections dynamically during iter_block_items,
        # but we can extract all headers and footers here.
        header_cache = {}
        footer_cache = {}
        
        for idx, section in enumerate(doc.sections):
            elements.append({"type": "section_start", "index": idx})
            
            # Header
            if not section.header.is_linked_to_previous or idx == 0:
                h_elements = []
                for block in iter_block_items(section.header):
                    if isinstance(block, Paragraph):
                        parsed = self._parse_paragraph(block)
                        if parsed: h_elements.extend(parsed)
                    elif isinstance(block, Table):
                        parsed = self._parse_table(block)
                        if parsed: h_elements.append(parsed)
                header_id = f"header_{idx}"
                header_cache[idx] = header_id
                elements.append({"type": "header", "id": header_id, "elements": h_elements, "is_new": True})
            else:
                # Link to previous
                elements.append({"type": "header", "id": header_cache.get(idx - 1, f"header_{idx-1}"), "is_new": False})
                header_cache[idx] = header_cache.get(idx - 1, f"header_{idx-1}")
                
            # Footer
            if not section.footer.is_linked_to_previous or idx == 0:
                f_elements = []
                for block in iter_block_items(section.footer):
                    if isinstance(block, Paragraph):
                        parsed = self._parse_paragraph(block)
                        if parsed: f_elements.extend(parsed)
                    elif isinstance(block, Table):
                        parsed = self._parse_table(block)
                        if parsed: f_elements.append(parsed)
                footer_id = f"footer_{idx}"
                footer_cache[idx] = footer_id
                elements.append({"type": "footer", "id": footer_id, "elements": f_elements, "is_new": True})
            else:
                elements.append({"type": "footer", "id": footer_cache.get(idx - 1, f"footer_{idx-1}"), "is_new": False})
                footer_cache[idx] = footer_cache.get(idx - 1, f"footer_{idx-1}")
        
        # 2. Process Body Items
        for block in iter_block_items(doc):
            if isinstance(block, Paragraph):
                parsed_p = self._parse_paragraph(block)
                if parsed_p:
                    elements.extend(parsed_p)
            elif isinstance(block, Table):
                parsed_t = self._parse_table(block)
                if parsed_t:
                    elements.append(parsed_t)
                    
        # Construct single-page document (flow layout)
        page_dict = {
            "page_num": 0,
            "elements": elements
        }
        
        cdo = CommonDocumentObject(
            document_id=file_metadata.get("document_id", "temp_doc_id"),
            fingerprint=file_metadata.get("fingerprint", "temp_fingerprint"),
            modality=self.modality,
            filename=file_metadata.get("filename", "unknown.docx"),
            mime_type=file_metadata.get("mime_type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            metadata=file_metadata,
            pages=[page_dict],
            text_blocks=[], # Deprecated for complex graphs
            tables=[]
        )
        
        self.emit_event("AdapterParsingCompleted", {"modality": self.modality})
        return cdo

    def _parse_paragraph(self, p: Paragraph) -> List[Dict[str, Any]]:
        """Parses a paragraph, including its text, style, and inline images."""
        text = p.text.strip()
        style_name = p.style.name if p.style else "Normal"
        
        results = []
        
        # Check for images inside paragraph XML
        image_parts = {}
        if hasattr(p.part, "rels"):
            for rel in p.part.rels.values():
                if "image" in rel.reltype:
                    image_parts[rel.rId] = (rel.target_part.blob, rel.target_part.content_type)

        # python-docx stores images in <w:drawing> tags inside <w:r>
        for run in p.runs:
            for drawing in run._r.findall('.//*{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
                for blip in drawing.findall('.//*{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
                    embed_id = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if embed_id and embed_id in image_parts:
                        img_bytes, mime = image_parts[embed_id]
                        # We append an image element preserving order
                        results.append({
                            "type": "image",
                            "image_bytes": img_bytes, # Real implementation might save and reference path, but requirements say route to VisionPipeline
                            "mime_type": mime,
                            "parent_style": style_name
                        })
        
        if not text:
            return results
            
        block_type = "paragraph"
        level = None
        
        # Detect Headings
        if style_name.startswith("Heading"):
            block_type = "heading"
            try:
                level = int(style_name.split()[-1])
            except ValueError:
                level = 1
        elif style_name == "Title":
            block_type = "heading"
            level = 0
                
        # Detect Lists
        elif "List" in style_name:
            block_type = "list"
            
        results.append({
            "type": block_type,
            "text": text,
            "style": style_name,
            "level": level,
            "formatting": self._extract_formatting(p)
        })
        
        return results

    def _extract_formatting(self, p: Paragraph) -> Dict[str, bool]:
        """Extracts basic semantic formatting from a paragraph."""
        has_bold = False
        has_italic = False
        has_underline = False
        
        for run in p.runs:
            if run.bold: has_bold = True
            if run.italic: has_italic = True
            if run.underline: has_underline = True
            
        return {
            "bold": has_bold,
            "italic": has_italic,
            "underline": has_underline
        }

    def _parse_table(self, table: Table) -> Dict[str, Any]:
        """Parses a table into structured rows and cells."""
        rows_data = []
        for r_idx, row in enumerate(table.rows):
            cells_data = []
            for c_idx, cell in enumerate(row.cells):
                cells_data.append({
                    "row_index": r_idx,
                    "col_index": c_idx,
                    "text": cell.text.strip()
                })
            rows_data.append({
                "row_index": r_idx,
                "cells": cells_data
            })
            
        return {
            "type": "table",
            "rows": rows_data,
            "num_rows": len(table.rows),
            "num_cols": len(table.columns) if table.columns else 0
        }
