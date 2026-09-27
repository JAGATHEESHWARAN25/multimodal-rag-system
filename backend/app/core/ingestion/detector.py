import os
import magic # Requires python-magic
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class FileValidationError(Exception):
    pass

class UnsupportedFormatError(FileValidationError):
    pass

class FileSizeError(FileValidationError):
    pass

class CorruptedFileError(FileValidationError):
    pass

class FileDetector:
    """
    Validates files before they enter the Ingestion Engine.
    Detects MIME type, size, extension, and checks for basic corruption.
    """
    
    MAX_FILE_SIZE_MB = 100
    
    # Supported valid MIME types mapped to extensions
    SUPPORTED_MIME_TYPES = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/webp': '.webp',
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/csv': '.csv',
        'application/csv': '.csv',
        'text/plain': '.txt',
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
        'audio/ogg': '.ogg',
        'audio/flac': '.flac',
        'audio/x-m4a': '.m4a',
        'video/mp4': '.mp4'
    }

    @classmethod
    def analyze_file(cls, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """
        Analyzes and validates the given file bytes.
        Returns a dictionary with file metadata if valid, else raises FileValidationError.
        """
        # 1. Empty File Check
        if not file_bytes:
            raise FileValidationError("File is empty.")
            
        # 2. File Size Check
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > cls.MAX_FILE_SIZE_MB:
            raise FileSizeError(f"File size {size_mb:.2f}MB exceeds maximum limit of {cls.MAX_FILE_SIZE_MB}MB.")
            
        # 3. MIME Type Detection via magic numbers
        try:
            mime_detector = magic.Magic(mime=True)
            detected_mime = mime_detector.from_buffer(file_bytes[:2048])
        except Exception as e:
            logger.warning(f"python-magic failed, falling back to basic extension check: {e}")
            detected_mime = cls._guess_mime_by_extension(original_filename)

        if detected_mime in ['application/octet-stream', 'application/zip']:
            if original_filename.endswith('.pptx'):
                detected_mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            elif original_filename.endswith('.docx'):
                detected_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif original_filename.endswith('.xlsx'):
                detected_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif detected_mime == 'text/plain' and original_filename.lower().endswith('.csv'):
            detected_mime = 'text/csv'

        # 4. Support Check
        if detected_mime not in cls.SUPPORTED_MIME_TYPES:
            raise UnsupportedFormatError(f"Unsupported MIME type: {detected_mime}")
            
        # 5. Extension Validation (prevent spoofing)
        _, ext = os.path.splitext(original_filename.lower())
        expected_ext = cls.SUPPORTED_MIME_TYPES[detected_mime]
        
        # Soft validation - some formats map to multiple extensions
        valid_exts = {expected_ext}
        if detected_mime == 'image/jpeg':
            valid_exts.update(['.jpg', '.jpeg'])
        elif detected_mime in ['text/plain']:
            valid_exts.update(['.txt', '.log', '.md', '.csv'])
        elif detected_mime in ['text/csv', 'application/csv']:
            valid_exts.update(['.csv', '.tsv'])
        elif detected_mime in ['audio/wav', 'audio/x-wav']:
            valid_exts.update(['.wav'])
        elif detected_mime in ['audio/mpeg', 'audio/mp3']:
            valid_exts.update(['.mp3'])
        elif detected_mime in ['audio/x-m4a']:
            valid_exts.update(['.m4a', '.mp4'])
        elif detected_mime in ['video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/webm', 'application/octet-stream']:
            valid_exts.update(['.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4a'])
            
        if ext not in valid_exts and ext != expected_ext:
            logger.warning(f"File extension spoofing detected: {original_filename} is actually {detected_mime}")
            raise UnsupportedFormatError(f"Extension spoofing detected: file claims to be {ext} but is {detected_mime}")
        
        return {
            "filename": original_filename,
            "mime_type": detected_mime,
            "size_bytes": len(file_bytes),
            "extension": ext
        }

    @classmethod
    def _guess_mime_by_extension(cls, filename: str) -> str:
        """Fallback when python-magic is unavailable (common on Windows without libmagic)."""
        import mimetypes
        mime, _ = mimetypes.guess_type(filename)
        return mime or "application/octet-stream"
