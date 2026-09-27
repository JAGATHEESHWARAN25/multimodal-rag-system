import io
import uuid
import logging
from typing import Dict, Any
import openpyxl
from openpyxl.utils import get_column_letter

from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.cache.fingerprint import DocumentFingerprinter

logger = logging.getLogger(__name__)

class XLSXAdapter(BaseAdapter):
    """
    Native Excel (.xlsx) Ingestion Adapter using openpyxl.
    Parses workbooks, worksheets, tables, rows, and cells safely into structured CommonDocumentObject pages.
    Excel Security: Never executes formulas, macros, or external code. Treats formulas strictly as raw text data.
    """

    def __init__(self):
        super().__init__()
        self.modality = "XLSX"

    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> CommonDocumentObject:
        filename = file_metadata.get("filename", "workbook.xlsx")
        document_id = str(uuid.uuid4())
        fingerprint = DocumentFingerprinter.generate_hash(file_bytes)

        # 1. Load openpyxl Workbook in data_only mode (returns values instead of formulas, never executes code)
        try:
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True, read_only=False)
        except Exception as e:
            logger.error(f"Failed to parse XLSX workbook {filename}: {e}")
            raise ValueError(f"Corrupted or invalid XLSX workbook: {e}")

        pages = []
        MAX_ROWS_PER_SHEET = 2000 # Memory & performance safety cap per sheet

        for page_num, sheet_name in enumerate(wb.sheetnames):
            ws = wb[sheet_name]
            
            # Extract Merged Cell Ranges
            merged_ranges = [str(r) for r in ws.merged_cells.ranges]

            rows_data = list(ws.iter_rows(values_only=False))
            if not rows_data:
                continue

            # Extract Headers from Row 1 if available
            header_cells = rows_data[0]
            headers = [str(c.value).strip() if c.value is not None else f"Column_{i+1}" for i, c in enumerate(header_cells)]
            
            body_rows = rows_data[1:] if len(rows_data) > 1 else []
            parsed_rows = []

            for r_idx, row in enumerate(body_rows[:MAX_ROWS_PER_SHEET], start=2):
                cell_objects = []
                for c_idx, cell in enumerate(row, start=1):
                    col_letter = get_column_letter(c_idx)
                    coord = f"{col_letter}{r_idx}"
                    cell_val = cell.value
                    val_str = str(cell_val).strip() if cell_val is not None else ""
                    col_name = headers[c_idx-1] if c_idx-1 < len(headers) else f"Column_{c_idx}"
                    
                    cell_objects.append({
                        "text": val_str,
                        "cell_coordinate": coord,
                        "row_index": r_idx,
                        "col_index": c_idx,
                        "column_name": col_name,
                        "number_format": cell.number_format or "",
                        "data_type": type(cell_val).__name__ if cell_val is not None else "empty"
                    })

                parsed_rows.append({
                    "row_index": r_idx,
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
                    "sheet_name": sheet_name,
                    "merged_ranges": merged_ranges,
                    "modality": "XLSX"
                }
            }

            pages.append({
                "page_num": page_num,
                "elements": [table_element],
                "text_blocks": [f"Sheet '{sheet_name}' with {len(headers)} columns and {len(parsed_rows)} rows. Headers: {', '.join(headers)}"],
                "metadata": {
                    "sheet_name": sheet_name
                }
            })

        wb.close()

        cdo = CommonDocumentObject(
            schema_version="2.0",
            document_id=document_id,
            fingerprint=fingerprint,
            modality="XLSX",
            filename=filename,
            mime_type=file_metadata.get("mime_type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            metadata={
                "sheet_count": len(pages),
                "sheet_names": wb.sheetnames,
                "total_pages": len(pages)
            },
            pages=pages
        )

        return cdo
