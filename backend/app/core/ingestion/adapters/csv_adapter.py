import csv
import io
import uuid
import logging
from typing import Dict, Any
from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.cache.fingerprint import DocumentFingerprinter

logger = logging.getLogger(__name__)

class CSVAdapter(BaseAdapter):
    """
    Native CSV Ingestion Adapter.
    Detects delimiters (comma, semicolon, tab) and parses tabular data into structured CommonDocumentObject tables, rows, and cells.
    """

    def __init__(self):
        super().__init__()
        self.modality = "CSV"

    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> CommonDocumentObject:
        filename = file_metadata.get("filename", "data.csv")
        document_id = str(uuid.uuid4())
        fingerprint = DocumentFingerprinter.generate_hash(file_bytes)

        # 1. Decode text
        decoded_text = self._decode_bytes(file_bytes)
        sample = decoded_text[:4096]

        # 2. Delimiter & Header Detection
        delimiter = ","
        has_header = True
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
            delimiter = dialect.delimiter
            has_header = sniffer.has_header(sample)
        except Exception as e:
            logger.warning(f"CSV Sniffer failed for {filename}, defaulting to comma delimiter: {e}")

        # 3. Native Parsing
        reader = csv.reader(io.StringIO(decoded_text), delimiter=delimiter)
        rows_data = list(reader)

        if not rows_data:
            headers = []
            body_rows = []
        elif has_header:
            headers = [h.strip() for h in rows_data[0]]
            body_rows = rows_data[1:]
        else:
            headers = [f"Column_{i+1}" for i in range(len(rows_data[0]))]
            body_rows = rows_data

        # 4. Build Structured Table Representation
        parsed_rows = []
        MAX_ROWS_LIMIT = 5000  # Enforce resource safety limit

        for row_idx, row_values in enumerate(body_rows[:MAX_ROWS_LIMIT], start=1):
            cell_objects = []
            for col_idx, cell_val in enumerate(row_values):
                val_str = cell_val.strip()
                col_name = headers[col_idx] if col_idx < len(headers) else f"Column_{col_idx+1}"
                data_type = self._infer_type(val_str)
                
                cell_objects.append({
                    "text": val_str,
                    "row_index": row_idx,
                    "col_index": col_idx,
                    "column_name": col_name,
                    "data_type": data_type
                })
                
            parsed_rows.append({
                "row_index": row_idx,
                "cells": cell_objects
            })

        table_element = {
            "type": "table",
            "id": str(uuid.uuid4()),
            "headers": headers,
            "num_rows": len(parsed_rows),
            "num_cols": len(headers),
            "rows": parsed_rows,
            "formatting": {
                "delimiter": delimiter,
                "modality": "CSV"
            }
        }

        page_structure = {
            "page_num": 0,
            "elements": [table_element],
            "text_blocks": [f"CSV Table '{filename}' with {len(headers)} columns and {len(parsed_rows)} rows. Columns: {', '.join(headers)}"]
        }

        cdo = CommonDocumentObject(
            schema_version="2.0",
            document_id=document_id,
            fingerprint=fingerprint,
            modality="CSV",
            filename=filename,
            mime_type=file_metadata.get("mime_type", "text/csv"),
            metadata={
                "delimiter": delimiter,
                "has_header": has_header,
                "column_count": len(headers),
                "row_count": len(parsed_rows),
                "total_rows_file": len(body_rows)
            },
            pages=[page_structure]
        )

        return cdo

    def _decode_bytes(self, file_bytes: bytes) -> str:
        for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                return file_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("Failed to decode CSV file bytes with supported encodings.")

    def _infer_type(self, val: str) -> str:
        if not val:
            return "empty"
        if val.isdigit():
            return "integer"
        try:
            float(val)
            return "float"
        except ValueError:
            pass
        return "text"
