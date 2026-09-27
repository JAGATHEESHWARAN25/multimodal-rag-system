import os
import uuid
import tempfile
import logging
from typing import Dict, Any
from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.cache.fingerprint import DocumentFingerprinter
from app.core.audio.engine import AudioTranscriptionEngine
from app.core.nlp.advanced_entity_extractor import AdvancedLocalEntityExtractor

logger = logging.getLogger(__name__)

class AudioAdapter(BaseAdapter):
    """
    Native Audio Ingestion Adapter.
    Processes speech audio files (WAV, MP3, OGG, M4A, FLAC) into timestamped
    CommonDocumentObject structures with segment-level knowledge representations.
    """

    def __init__(self):
        super().__init__()
        self.modality = "audio"

    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> CommonDocumentObject:
        filename = file_metadata.get("filename", "audio_recording.wav")
        document_id = file_metadata.get("document_id") or str(uuid.uuid4())
        classification = file_metadata.get("classification", "PUBLIC")
        fingerprint = DocumentFingerprinter.generate_hash(file_bytes)

        # Write file temporarily to disk for audio reading
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            metadata = AudioTranscriptionEngine.get_audio_metadata(tmp_path)
            segments = AudioTranscriptionEngine.transcribe(tmp_path, classification=classification)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # Build CommonDocumentObject pages from audio segments
        # Each segment functions as a time-indexed document block
        pages = []
        entity_extractor = AdvancedLocalEntityExtractor()
        all_transcript_texts = []

        for idx, seg in enumerate(segments, start=1):
            text = seg.get("text", "")
            all_transcript_texts.append(text)
            
            # Extract entities from transcript segment
            entities = entity_extractor.extract_entities(text)
            
            pages.append({
                "page_num": idx,
                "text_blocks": [text],
                "elements": [
                    {
                        "type": "audio_segment",
                        "id": str(uuid.uuid4()),
                        "text": text,
                        "start_time": seg.get("start_time", 0.0),
                        "end_time": seg.get("end_time", 0.0),
                        "timestamp_str": seg.get("timestamp_str", "00:00 - 00:00"),
                        "confidence": seg.get("confidence", 1.0),
                        "entities": entities
                    }
                ],
                "metadata": {
                    "duration_seconds": metadata.get("duration_seconds", 0.0),
                    "sample_rate": metadata.get("sample_rate", 16000),
                    "channels": metadata.get("channels", 1),
                    "start_time": seg.get("start_time", 0.0),
                    "end_time": seg.get("end_time", 0.0),
                    "timestamp_str": seg.get("timestamp_str", "00:00 - 00:00")
                }
            })

        cdo = CommonDocumentObject(
            document_id=document_id,
            fingerprint=fingerprint,
            modality="audio",
            filename=filename,
            mime_type=file_metadata.get("mime_type", "audio/wav"),
            classification=classification,
            pages=pages,
            metadata={
                "duration_seconds": metadata.get("duration_seconds", 0.0),
                "sample_rate": metadata.get("sample_rate", 16000),
                "channels": metadata.get("channels", 1),
                "segment_count": len(segments),
                "full_transcript": " ".join(all_transcript_texts)
            }
        )

        return cdo
