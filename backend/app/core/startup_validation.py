import os
import sys
import platform
import logging
import psutil
from pathlib import Path
import cv2
import sqlite3

# Basic imports to verify core libraries are present
try:
    import chromadb
    import paddleocr
    import pytesseract
except ImportError as e:
    raise ImportError(f"CRITICAL DEPENDENCY MISSING: {e}")

logger = logging.getLogger(__name__)

def validate_environment(config_module):
    """
    Runs a pre-flight checklist.
    Exits application with code 1 if any critical dependencies are missing.
    """
    logger.info("--- Starting Environment Validation ---")
    
    # 1. Python Version
    version = sys.version_info
    logger.info(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        logger.error("Python 3.9+ is required.")
        sys.exit(1)
        
    # 2. Virtual Environment Check
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.warning("WARNING: Not running inside a virtual environment.")
        
    # 3. Hardware Checks
    ram_gb = psutil.virtual_memory().total / (1024**3)
    logger.info(f"Available RAM: {ram_gb:.2f} GB")
    if ram_gb < 8.0:
        logger.warning("Less than 8GB RAM detected. Performance may be degraded.")
        
    # 4. Tesseract Path
    if not os.path.exists(config_module.TESSERACT_PATH):
        logger.error(f"Tesseract executable NOT FOUND at {config_module.TESSERACT_PATH}")
        sys.exit(1)
    logger.info("Tesseract executable found.")
    
    # 5. Data Directories Writable
    dirs_to_check = [
        config_module.UPLOADS_DIR,
        config_module.PROCESSED_DIR, 
        config_module.SQLITE_DIR,
        config_module.CHROMA_DIR
    ]
    for d in dirs_to_check:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test_file = d / ".write_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            logger.error(f"Directory {d} is not writable: {e}")
            sys.exit(1)
    logger.info("All data directories are writable.")
            
    # 6. OpenCV Verification
    logger.info(f"OpenCV Version: {cv2.__version__}")
    
    # 7. SQLite Verification
    logger.info(f"SQLite Version: {sqlite3.sqlite_version}")
    
    logger.info("--- Environment Validation Passed ---")
    return True

if __name__ == "__main__":
    from app import config
    validate_environment(config)
