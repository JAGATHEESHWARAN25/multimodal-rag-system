import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from app.config import UPLOADS_DIR
from app.models.database import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Upload & Image Management"])

# Permitted image file extensions
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
# Maximum allowed file size: 10 MB in bytes
MAX_FILE_SIZE = 10 * 1024 * 1024 

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_images(files: list[UploadFile] = File(...)):
    """Receives one or multiple images, validates them, and stores them on local disk.
    
    Validations:
      - File extension must be in ['.png', '.jpg', '.jpeg']
      - File size must be less than or equal to 10MB
    """
    uploaded_records = []
    
    for file in files:
        filename = file.filename
        file_ext = Path(filename).suffix.lower()
        
        # 1. Validate extension
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' has an invalid extension. Supported: PNG, JPG, JPEG."
            )
            
        # 2. Check file size. FastAPI UploadFile objects can read spool sizes
        # To avoid caching the entire file in memory, we read the size in chunks
        size = 0
        temp_chunks = []
        try:
            while True:
                chunk = await file.read(64 * 1024) # Read in 64KB blocks
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File '{filename}' exceeds the maximum allowed size of 10MB."
                    )
                temp_chunks.append(chunk)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Error reading file '{filename}': {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read upload stream for: {filename}"
            )
            
        # 3. Generate unique identifier and storage path
        image_id = str(uuid.uuid4())
        safe_filename = f"{image_id}{file_ext}"
        storage_path = UPLOADS_DIR / safe_filename
        
        # 4. Write verified chunks to disk
        try:
            with open(storage_path, "wb") as out_file:
                for chunk in temp_chunks:
                    out_file.write(chunk)
        except IOError as e:
            logger.error(f"Failed to write file '{filename}' to disk: {str(e)}")
            # Cleanup if partially written
            if storage_path.exists():
                os.remove(storage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FileSystem error. Failed to save upload on server disk."
            )
            
        # 5. Insert record into database registry
        try:
            record = DatabaseManager.add_image(
                image_id=image_id,
                filename=filename,
                storage_path=storage_path,
                file_size=size,
                mime_type=file.content_type or "image/png"
            )
            uploaded_records.append(record)
        except Exception as e:
            logger.error(f"Database error writing record for '{filename}': {str(e)}")
            # Rollback file write
            if storage_path.exists():
                os.remove(storage_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error. Failed to index upload metadata."
            )
            
    return uploaded_records

@router.get("/images")
def get_images():
    """Lists metadata for all uploaded documents in the database registry."""
    try:
        return DatabaseManager.get_all_images()
    except Exception as e:
        logger.error(f"Database read query failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Failed to query image registry."
        )

@router.get("/images/{image_id}/raw")
def get_raw_image(image_id: str):
    """Serves the raw image file directly to browser client previews."""
    record = DatabaseManager.get_image(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found in the database registry."
        )
        
    storage_path = Path(record["storage_path"])
    if not storage_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file missing from server disk storage."
        )
        
    return FileResponse(str(storage_path), media_type=record["mime_type"])

@router.delete("/images/{image_id}")
def delete_image(image_id: str):
    """Deletes an image physically from the disk storage, clears all processing caches, and removes vector index."""
    record = DatabaseManager.get_image(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found in the database registry."
        )
        
    # 1. Remove raw file from local disk storage
    storage_path = Path(record["storage_path"])
    if storage_path.exists():
        try:
            os.remove(storage_path)
        except OSError as e:
            logger.error(f"Failed to physically delete file at {storage_path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to physically delete file from server storage."
            )
            
    # 2. Clean associated processing outputs and OCR text/JSON caches
    from app.config import PROCESSED_DIR, OCR_OUTPUT_DIR
    processed_path = PROCESSED_DIR / f"{image_id}_processed.png"
    txt_path = OCR_OUTPUT_DIR / f"{image_id}.txt"
    json_path = OCR_OUTPUT_DIR / f"{image_id}.json"
    chunks_path = OCR_OUTPUT_DIR / f"{image_id}_chunks.json"
    overlay_path = OCR_OUTPUT_DIR / f"{image_id}_overlay.png"

    for path in (processed_path, txt_path, json_path, chunks_path, overlay_path):
        if path.exists():
            try:
                os.remove(path)
            except OSError:
                pass

    # 3. Delete indexed embeddings from local vector database
    try:
        from app.core.vectordb import VectorDatabaseManager
        VectorDatabaseManager.delete_document_indices("document_chunks", image_id)
    except Exception as e:
        logger.error(f"Failed to clean vector database indexes for {image_id}: {str(e)}")
            
    # 4. Remove database index from SQLite
    try:
        deleted = DatabaseManager.delete_image(image_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Metadata delete command failed."
            )
    except Exception as e:
        logger.error(f"Database delete transaction failed for {image_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Failed to delete file index."
        )
        
    return {"message": "Image and associated index/caches successfully deleted."}
