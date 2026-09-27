# PDF Adapter

The PDF Adapter is responsible for safely, efficiently, and accurately extracting metadata, text, images, and tables from incoming PDF files and mapping them into the standardized `CommonDocumentObject` (CDO) format.

## Architecture
To future-proof the document intelligence platform, the adapter is completely decoupled from any single underlying library. It communicates strictly through two abstract interfaces:
1. `BasePDFEngine` - Handles file opening, parsing, and page-level text/image extraction.
2. `BaseTableExtractor` - Dedicated exclusively to understanding tables.

### Data Flow
1. PDF bytes enter `PDFAdapter.parse()`.
2. `BasePDFEngine` extracts metadata.
3. The adapter requests the optimal `batch_size` from the `ResourceManager`.
4. Pages are iterated over:
   - Native text and images are extracted.
   - If missing (e.g. Scanned PDF), the page is natively rendered to an image.
   - Tables are extracted via `BaseTableExtractor`.
5. Every `batch_size` pages, a `CommonDocumentObject` is yielded.
6. Downstream (Pipeline Orchestrator) maps the CDO to Knowledge Objects for immediate incremental indexing.

## Available Engines & Licensing

### PyMuPDF (Default for Phase 2)
- **License**: GNU AGPL 3.0 (Commercial license available from Artifex).
- **Advantages**: The absolute fastest PDF library available for Python. It binds directly to the C/C++ MuPDF engine. Native rendering, exceptional image extraction, low RAM usage.
- **Limitations**: AGPL limits usage in hosted, multi-tenant SaaS architectures without purchasing a commercial license. Not an issue for local, offline tooling.
- **Offline Compatibility**: 100% offline.
- **Performance**: High (O(ms) per page).
- **Enterprise Suitability**: High (if commercial license is acquired for cloud deployments).

### Future Candidate Engines
* **pdfplumber** (MIT License) - Excellent for complex tables and layout preservation. Extremely slow. High RAM. Best used as a secondary table extraction engine.
* **pypdf** (BSD License) - Pure Python, highly permissive. Struggles with complex image extraction and layout bugs.
* **PDFium** (Apache 2.0) - C++ based (Google). Very fast, but Python bindings (`pypdfium2`) have steeper learning curves than PyMuPDF. Excellent permissive alternative.

## Table Extraction
Table extraction is isolated to `BaseTableExtractor`. Currently, a `NativeTableExtractor` serves as a placeholder. In future phases, libraries like `pdfplumber`, `Camelot`, or `Tabula` can be implemented and dynamically injected into the `PDFAdapter` without modifying the core pipeline.
