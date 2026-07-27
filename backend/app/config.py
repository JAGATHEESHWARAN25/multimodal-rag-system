import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_env_file(env_path: Path):
    """Loads variables from .env file into os.environ if present."""
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    # Strip quotes if present
                    if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                        val = val[1:-1]
                    os.environ.setdefault(key, val)

# Load configuration from the backend/.env file
load_env_file(BASE_DIR / "backend" / ".env")

# Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Tesseract executable path setting
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# Chunking configurations
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))

# Core Directories configuration
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
OCR_OUTPUT_DIR = DATA_DIR / "ocr_cache"
SQLITE_DIR = DATA_DIR / "sqlite"
SQLITE_DB_PATH = SQLITE_DIR / "metadata.db"
CHROMA_DIR = DATA_DIR / "chroma"
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-base-en-v1.5")

# Create directories if they do not exist
for path in [DATA_DIR, UPLOADS_DIR, PROCESSED_DIR, OCR_OUTPUT_DIR, SQLITE_DIR, CHROMA_DIR]:
    path.mkdir(parents=True, exist_ok=True)
