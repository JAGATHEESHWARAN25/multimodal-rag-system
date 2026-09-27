import os

docs_dir = "backend/docs"
os.makedirs(docs_dir, exist_ok=True)

docs = [
    "architecture.md", "pipeline.md", "model_manager.md", 
    "quality_module.md", "classification.md", "ocr.md", 
    "schema.md", "chunking.md", "testing.md", "benchmark.md"
]

content_template = """# {title}
## Phase 1.5 Baseline Documentation

### Purpose
Provides standard interfaces and processing contracts for this module.

### Architecture
Integrates cleanly with the Adapter pattern and Common Document Object.

### Configuration
Externalized in `config.py`.

### Dependencies & Future
Prepared for Phase 2: Universal Document Understanding.
"""

for doc in docs:
    title = doc.replace(".md", "").replace("_", " ").title()
    with open(os.path.join(docs_dir, doc), "w", encoding="utf-8") as f:
        f.write(content_template.format(title=title))

print("Documentation generated.")
