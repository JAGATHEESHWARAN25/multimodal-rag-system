# Document Classification & Role-Based Access Control (RBAC) Specification
## Review-2 Standard Security Architecture

### 1. Document Classification Levels
The system implements a 5-tier hierarchical security classification model:

| Classification | Sensitivity Level | Permitted Roles |
| :--- | :--- | :--- |
| **PUBLIC** | Unclassified / Open | `ALL ROLES` (Viewer, Reviewer, Document Officer, Intelligence Analyst, System Admin) |
| **INTERNAL** | General Staff / Non-Public | `VIEWER`, `STANDARD_USER`, `REVIEWER`, `AUDITOR`, `DOCUMENT_OFFICER`, `INTELLIGENCE_ANALYST`, `SYSTEM_ADMIN` |
| **CONFIDENTIAL**| Compartmented Review | `REVIEWER`, `AUDITOR`, `DOCUMENT_OFFICER`, `INTELLIGENCE_ANALYST`, `SYSTEM_ADMIN` |
| **SECRET** | Mission Critical Operational | `DOCUMENT_OFFICER`, `INTELLIGENCE_ANALYST`, `SYSTEM_ADMIN` |
| **TOP_SECRET** | Highest Strategic Security | `INTELLIGENCE_ANALYST`, `SYSTEM_ADMIN` |

### 2. User Roles & Capabilities
The canonical roles configured in `app.core.security.Role`:

- **`SYSTEM_ADMIN`**: Full platform authority. User management, system configuration, audit log inspection, document deletion, and top-secret clearance.
- **`INTELLIGENCE_ANALYST`**: Full investigative capabilities. Multimodal RAG querying, Knowledge Graph reasoning, semantic search, document summarization, top-secret clearance, document upload.
- **`DOCUMENT_OFFICER`**: Ingestion, lifecycle, and document management. Document upload, batch processing, document deletion (`/api/images/{id}`), metadata management, clearance up to SECRET.
- **`REVIEWER`**: Quality verification and analytical review. Document inspection, OCR validation, Knowledge Graph exploration, clearance up to CONFIDENTIAL.
- **`VIEWER`**: Read-only access to authorized public and internal documents and gallery.
- **`AUDITOR`** *(Alias / Security Auditor)*: Audit log monitoring, compliance verification, and system health inspection.
- **`STANDARD_USER`** *(Alias)*: Standard organizational viewer.

### 3. Enforcement Points
1. **Gallery & Listing (`GET /api/images`)**: Strictly filters all document metadata. Unauthorized document records are never returned to client.
2. **Raw & Thumbnail Content (`GET /api/images/{id}/raw`, `/thumbnail`, `/html`)**: Token authorization and clearance validation prior to disk file streaming.
3. **OCR & Text Endpoints (`GET /api/images/{id}/ocr/*`)**: Enforces classification clearance before serving extracted text, OCR confidence, or chunk partitions.
4. **Vector Search & Chat (`GET /api/images/search`, `POST /api/chat`)**: Filters vector chunk candidates and Graph-RAG relationship expansions by user context clearance.
5. **Knowledge Graph (`/api/graph/*`)**: Traversal, neighborhood queries, and visualization prune all nodes and edges belonging to documents above the user's clearance.

