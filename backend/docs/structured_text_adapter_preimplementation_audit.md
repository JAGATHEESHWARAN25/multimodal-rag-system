# Pre-Implementation Audit & Technical Architecture: TXT, CSV, and XLSX Adapters

## 1. Existing Architecture
The Offline Multimodal RAG Platform processes documents using a unified ingestion pipeline:

```
File Upload (PDF, DOCX, PPTX, Image, TXT, CSV, XLSX)
                 |
                 v
       FileDetector (MIME & extension validation)
                 |
                 v
        AdapterManager & BaseAdapter
                 |
                 v
       CommonDocumentObject (CDO)
                 |
                 v
        PipelineOrchestrator
                 |
                 v
   UniversalKnowledgeSchema + KnowledgeObjects
                 |
        +--------+--------+
        |                 |
        v                 v
SQLite Knowledge Graph   ChromaDB Vector Store
        |                 |
        +--------+--------+
                 |
                 v
   UniversalMultimodalQueryService
```

## 2. Existing Reusable Components
- **`FileDetector`** (`app/core/ingestion/detector.py`): Validates file size, MIME types, and extension spoofing.
- **`AdapterManager`** (`app/core/ingestion/adapters/manager.py`): Global registry for MIME-to-Adapter mapping.
- **`BaseAdapter`** (`app/core/ingestion/adapters/base.py`): Abstract base class for adapters returning `CommonDocumentObject`.
- **`CommonDocumentObject`** (`app/models/schema.py`): Normalization model containing pages, elements, tables, and metadata.
- **`PipelineOrchestrator`** (`app/core/pipeline/orchestrator.py`): Converts CDO to `KnowledgeObject` nodes, `RelationshipEdge` links, extracts entities via `EntityExtractor`, and builds ChromaDB vectors via `SemanticChunker`.
- **`DatabaseManager`** (`app/models/database.py`): Persists knowledge objects, relationship edges, documents, and chat sessions in SQLite.
- **`VectorDatabaseManager`** (`app/core/vectordb.py`): Handles semantic vector indexing and similarity queries in ChromaDB.
- **`UniversalMultimodalQueryService`** (`app/core/rag/universal_query.py`): Multi-modal RAG query orchestrator.
- **`ResourceManager`** (`app/core/resource_manager.py`): Manages CPU memory limits and batching for large document processing.

## 3. Required Files to Create/Modify

### New Adapter Files:
- `backend/app/core/ingestion/adapters/txt_adapter.py`
- `backend/app/core/ingestion/adapters/csv_adapter.py`
- `backend/app/core/ingestion/adapters/xlsx_adapter.py`

### Modified Engine & Core Files:
- `backend/app/core/ingestion/__init__.py` (Register `TXTAdapter`, `CSVAdapter`, `XLSXAdapter`)
- `backend/app/core/ingestion/detector.py` (Add zip fallback mapping for `.xlsx`)
- `backend/app/core/pipeline/orchestrator.py` (Support TXT, CSV, XLSX structural block parsing, row/cell knowledge objects, and entity extraction over cells/paragraphs)
- `backend/app/core/chunking.py` (Preserve cell/row/sheet metadata in vector chunk metadata)
- `backend/app/core/rag/universal_query.py` (Include TXT, CSV, XLSX in input understanding, related knowledge discovery, and citation building)
- `backend/requirements.txt` (Add `openpyxl>=3.1.0`)

### New Backend Test Files:
- `backend/tests/test_txt_adapter.py`
- `backend/tests/test_csv_adapter.py`
- `backend/tests/test_xlsx_adapter.py`
- `backend/tests/test_structured_modalities.py`

### Modified Frontend Files & Tests:
- `frontend/src/App.jsx` (Add `.txt`, `.csv`, `.xlsx` file support, modality icons, and structured text/table inspector modals)
- `frontend/src/__tests__/App.test.jsx` (Add tests for TXT, CSV, XLSX attachments and inspectors)

### Reports & Demonstration Files:
- `backend/docs/csv_xlsx_txt_implementation_report.md`
- Demonstration dataset in `backend/demo_data/`:
  - `government_style_report.txt`
  - `network_inventory.csv`
  - `infrastructure_inventory.xlsx`

## 4. Dependencies Assessment
- **Installed**: `openpyxl` (version 3.1.5 is already installed in the environment), standard library `csv`, `mimetypes`, `python-magic`.
- **To Add**: Add `openpyxl>=3.1.0` to `backend/requirements.txt`.
- **No external services required**: Excel parsing remains 100% offline and pythonic using `openpyxl` with `read_only=True` for large files.

## 5. Compatibility Risks & Mitigation
- **Excel Security**: Formulas must be read as raw strings/data without execution; macros and embedded code are ignored.
- **Large Files**: CSV and XLSX files can contain thousands of rows. The adapters use streaming generator patterns and row limit thresholds to prevent RAM spikes, respecting `ResourceManager`.
- **Extension Spoofing**: `FileDetector` checks MIME magic headers first before trusting file extensions.

## 6. Proposed Graph Representation

### TXT Graph Structure:
```
Document
  └── Page 1
       ├── Section (Heading)
       │    ├── Paragraph
       │    └── Paragraph
       └── Section (Heading)
            └── Paragraph
```

### CSV Graph Structure:
```
Document
  └── Table
       ├── Row 1 (Header)
       │    ├── Cell A1
       │    └── Cell B1
       └── Row 2
            ├── Cell A2
            └── Cell B2
```

### XLSX Graph Structure:
```
Document
  └── Workbook
       ├── Sheet "Servers"
       │    └── Table
       │         ├── Row 1
       │         └── Row 2
       └── Sheet "Network"
            └── Table
                 └── Row 1
```

## 7. Proposed Citation Representation
- **TXT**: `{ "document_id": "...", "filename": "report.txt", "modality": "TXT", "line_number": 42, "text": "Snippet..." }`
- **CSV**: `{ "document_id": "...", "filename": "inventory.csv", "modality": "CSV", "row_index": 5, "column_name": "ServerIP", "text": "10.0.0.1" }`
- **XLSX**: `{ "document_id": "...", "filename": "network.xlsx", "modality": "XLSX", "sheet_name": "Inventory", "cell_coordinate": "B12", "row_index": 12, "column_index": 2, "text": "Authentication Server" }`

## 8. Test Strategy
50+ new unit, security, RBAC, background job, cache hit, and integration tests across 4 test suites verifying all acceptance criteria.
