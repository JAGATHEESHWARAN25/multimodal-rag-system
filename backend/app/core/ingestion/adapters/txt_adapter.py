import uuid
import logging
from typing import Dict, Any, Union, Generator
from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.cache.fingerprint import DocumentFingerprinter

logger = logging.getLogger(__name__)

class TXTAdapter(BaseAdapter):
    """
    Native Plain Text (.txt) Ingestion Adapter.
    Parses plain text safely into structured CommonDocumentObject sections and paragraphs.
    Handles UTF-8, UTF-8 BOM, fallback encodings, and rejects binary content.
    """

    def __init__(self):
        super().__init__()
        self.modality = "TXT"

    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> CommonDocumentObject:
        filename = file_metadata.get("filename", "document.txt")
        document_id = str(uuid.uuid4())
        fingerprint = DocumentFingerprinter.generate_hash(file_bytes)

        # 1. Binary Check: Reject files with high null byte ratio or binary control characters
        if b'\x00' in file_bytes[:1024]:
            raise ValueError(f"File {filename} contains binary null bytes and cannot be parsed as plain text.")

        # 2. Safe Decoding
        decoded_text = self._decode_bytes(file_bytes)

        # 3. Structural Parsing into Paragraphs and Sections
        lines = decoded_text.splitlines()
        elements = []
        current_section = "General"
        paragraph_buffer = []
        start_line = 1

        for line_idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            # Detect section heading heuristic: all caps, short line ending with colon, or markdown heading '#'
            if (stripped.startswith("#") or (len(stripped) < 80 and stripped.isupper()) or (stripped.endswith(":") and len(stripped) < 60)) and len(stripped) > 2:
                # Flush previous paragraph buffer
                if paragraph_buffer:
                    para_text = " ".join(paragraph_buffer).strip()
                    if para_text:
                        elements.append({
                            "type": "paragraph",
                            "id": str(uuid.uuid4()),
                            "text": para_text,
                            "section": current_section,
                            "formatting": {
                                "start_line": start_line,
                                "end_line": line_idx - 1,
                                "modality": "TXT"
                            }
                        })
                    paragraph_buffer = []

                clean_heading = stripped.lstrip("#").strip().rstrip(":")
                current_section = clean_heading
                elements.append({
                    "type": "heading",
                    "id": str(uuid.uuid4()),
                    "text": clean_heading,
                    "level": 1,
                    "formatting": {
                        "line_number": line_idx,
                        "modality": "TXT"
                    }
                })
                start_line = line_idx + 1
            elif not stripped:
                # Empty line marks paragraph boundary
                if paragraph_buffer:
                    para_text = " ".join(paragraph_buffer).strip()
                    if para_text:
                        elements.append({
                            "type": "paragraph",
                            "id": str(uuid.uuid4()),
                            "text": para_text,
                            "section": current_section,
                            "formatting": {
                                "start_line": start_line,
                                "end_line": line_idx - 1,
                                "modality": "TXT"
                            }
                        })
                    paragraph_buffer = []
                start_line = line_idx + 1
            else:
                if not paragraph_buffer:
                    start_line = line_idx
                paragraph_buffer.append(stripped)

        # Flush final paragraph buffer
        if paragraph_buffer:
            para_text = " ".join(paragraph_buffer).strip()
            if para_text:
                elements.append({
                    "type": "paragraph",
                    "id": str(uuid.uuid4()),
                    "text": para_text,
                    "section": current_section,
                    "formatting": {
                        "start_line": start_line,
                        "end_line": len(lines),
                        "modality": "TXT"
                    }
                })

        page_structure = {
            "page_num": 0,
            "width": 0,
            "height": 0,
            "elements": elements,
            "text_blocks": [el["text"] for el in elements if "text" in el]
        }

        cdo = CommonDocumentObject(
            schema_version="2.0",
            document_id=document_id,
            fingerprint=fingerprint,
            modality="TXT",
            filename=filename,
            mime_type=file_metadata.get("mime_type", "text/plain"),
            metadata={
                "total_lines": len(lines),
                "total_elements": len(elements),
                "encoding_used": getattr(self, "_last_encoding", "utf-8")
            },
            pages=[page_structure]
        )

        return cdo

    def _decode_bytes(self, file_bytes: bytes) -> str:
        """Safely decodes bytes trying utf-8-sig (BOM), utf-8, latin-1, and cp1252."""
        for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                decoded = file_bytes.decode(enc).lstrip('\ufeff')
                self._last_encoding = enc
                return decoded
            except UnicodeDecodeError:
                continue
        raise ValueError("Failed to decode text file with supported encodings (UTF-8, Latin-1, CP1252).")
