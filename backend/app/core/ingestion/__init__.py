from app.core.ingestion.engine import IngestionEngine
from app.core.ingestion.adapters.manager import AdapterManager
from app.core.ingestion.adapters.image_adapter import ImageAdapter
from app.core.ingestion.adapters.pdf_adapter import PDFAdapter
from app.core.ingestion.adapters.docx_adapter import DOCXAdapter
from app.core.ingestion.adapters.pptx_adapter import PPTXAdapter
from app.core.ingestion.adapters.txt_adapter import TXTAdapter
from app.core.ingestion.adapters.csv_adapter import CSVAdapter
from app.core.ingestion.adapters.xlsx_adapter import XLSXAdapter
from app.core.ingestion.adapters.audio_adapter import AudioAdapter
from app.core.ingestion.adapters.video_adapter import VideoAdapter

# Register core adapters on module initialization
AdapterManager.register_adapter(
    mime_types=['image/png', 'image/jpeg', 'image/webp'],
    adapter_class=ImageAdapter
)

AdapterManager.register_adapter(
    mime_types=['application/pdf'],
    adapter_class=PDFAdapter
)

AdapterManager.register_adapter(
    mime_types=[
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ],
    adapter_class=DOCXAdapter
)

AdapterManager.register_adapter(
    mime_types=[
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-powerpoint'
    ],
    adapter_class=PPTXAdapter
)

AdapterManager.register_adapter(
    mime_types=['text/plain'],
    adapter_class=TXTAdapter
)

AdapterManager.register_adapter(
    mime_types=['text/csv', 'application/csv'],
    adapter_class=CSVAdapter
)

AdapterManager.register_adapter(
    mime_types=['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    adapter_class=XLSXAdapter
)

AdapterManager.register_adapter(
    mime_types=[
        'audio/wav',
        'audio/x-wav',
        'audio/mpeg',
        'audio/mp3',
        'audio/ogg',
        'audio/x-m4a',
        'audio/flac'
    ],
    adapter_class=AudioAdapter
)

AdapterManager.register_adapter(
    mime_types=[
        'video/mp4',
        'video/x-msvideo',
        'video/quicktime',
        'video/x-matroska',
        'video/webm'
    ],
    adapter_class=VideoAdapter
)

__all__ = ['IngestionEngine', 'AdapterManager']
