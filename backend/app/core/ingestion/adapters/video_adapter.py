import os
import uuid
import tempfile
import subprocess
import logging
import cv2
from typing import Dict, Any, Optional, List

from app.core.ingestion.adapters.base import BaseAdapter
from app.models.schema import CommonDocumentObject
from app.core.cache.fingerprint import DocumentFingerprinter
from app.core.audio.engine import AudioTranscriptionEngine
from app.core.nlp.advanced_entity_extractor import AdvancedLocalEntityExtractor

logger = logging.getLogger(__name__)

class VideoAdapter(BaseAdapter):
    """
    Native Video Ingestion Adapter.
    Processes video files (MP4, AVI, MOV, MKV, WEBM) into timestamped
    CommonDocumentObject structures with audio speech transcripts, keyframe scene sampling,
    and frame OCR text.
    """

    def __init__(self):
        super().__init__()
        self.modality = "video"

    def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extracts mono 16kHz WAV audio track from video file using imageio-ffmpeg or ffmpeg."""
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            tmp_wav = tempfile.mktemp(suffix=".wav")
            cmd = [
                ffmpeg_exe, "-y", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                tmp_wav
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=60)
            if res.returncode == 0 and os.path.exists(tmp_wav) and os.path.getsize(tmp_wav) > 100:
                return tmp_wav
        except Exception as e:
            logger.warning(f"Audio extraction from video failed: {e}")
        return None

    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> CommonDocumentObject:
        filename = file_metadata.get("filename", "video.mp4")
        document_id = file_metadata.get("document_id") or str(uuid.uuid4())
        classification = file_metadata.get("classification", "PUBLIC")
        fingerprint = DocumentFingerprinter.generate_hash(file_bytes)

        suffix = os.path.splitext(filename)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_video_path = tmp.name

        wav_path = None
        audio_segments = []
        try:
            # 1. Extract audio track and transcribe speech
            wav_path = self._extract_audio(tmp_video_path)
            if wav_path:
                audio_segments = AudioTranscriptionEngine.transcribe(wav_path, classification=classification)
        except Exception as e:
            logger.warning(f"Video audio transcription step failed: {e}")
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass

        # 2. Keyframe sampling & Video Properties via OpenCV
        keyframes_dir = os.path.join("data", "keyframes", document_id)
        os.makedirs(keyframes_dir, exist_ok=True)

        cap = cv2.VideoCapture(tmp_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_sec = round(total_frames / fps, 2) if fps > 0 else 0.0

        # Sample keyframe every 4 seconds or at least 1 keyframe
        sample_interval_sec = 4.0
        sample_frame_step = max(1, int(fps * sample_interval_sec))
        
        keyframes = []
        entity_extractor = AdvancedLocalEntityExtractor()
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_frame_step == 0 or frame_idx == 0:
                current_sec = round(frame_idx / fps, 2)
                frame_file = os.path.join(keyframes_dir, f"frame_{int(current_sec)}s.jpg")
                cv2.imwrite(frame_file, frame)
                
                # Perform basic OCR on keyframe if screen/slides contain text
                ocr_text = ""
                try:
                    from app.core.ocr import LocalOCREngine
                    ocr_res = LocalOCREngine.extract_text(frame)
                    if isinstance(ocr_res, dict):
                        ocr_text = ocr_res.get("text", "").strip()
                    elif isinstance(ocr_res, str):
                        ocr_text = ocr_res.strip()
                except Exception:
                    pass

                keyframes.append({
                    "time_sec": current_sec,
                    "frame_path": frame_file.replace("\\", "/"),
                    "ocr_text": ocr_text
                })
            frame_idx += 1
        cap.release()

        # Clean up temporary video file
        if os.path.exists(tmp_video_path):
            try:
                os.remove(tmp_video_path)
            except Exception:
                pass

        # 3. Assemble unified video segments (combining audio speech transcript & frame OCR)
        pages = []
        all_texts = []

        if audio_segments:
            for idx, seg in enumerate(audio_segments, start=1):
                start_sec = seg.get("start_time", 0.0)
                end_sec = seg.get("end_time", 0.0)
                speech_text = seg.get("text", "")

                matching_ocr = [
                    kf["ocr_text"] for kf in keyframes
                    if start_sec <= kf["time_sec"] <= end_sec + 2.0 and kf["ocr_text"]
                ]
                combined_text = speech_text
                if matching_ocr:
                    combined_text += "\n[On-Screen Visual Text]: " + " ".join(matching_ocr)

                all_texts.append(combined_text)
                entities = entity_extractor.extract_entities(combined_text)

                pages.append({
                    "page_num": idx,
                    "text_blocks": [combined_text],
                    "elements": [
                        {
                            "type": "video_segment",
                            "id": str(uuid.uuid4()),
                            "text": combined_text,
                            "start_time": start_sec,
                            "end_time": end_sec,
                            "timestamp_str": seg.get("timestamp_str", f"{AudioTranscriptionEngine._format_timestamp(start_sec)} - {AudioTranscriptionEngine._format_timestamp(end_sec)}"),
                            "confidence": seg.get("confidence", 1.0),
                            "entities": entities
                        }
                    ],
                    "metadata": {
                        "duration_seconds": duration_sec,
                        "fps": fps,
                        "start_time": start_sec,
                        "end_time": end_sec,
                        "timestamp_str": seg.get("timestamp_str", f"{AudioTranscriptionEngine._format_timestamp(start_sec)} - {AudioTranscriptionEngine._format_timestamp(end_sec)}")
                    }
                })
        else:
            for idx, kf in enumerate(keyframes, start=1):
                t_sec = kf["time_sec"]
                t_end = min(duration_sec, t_sec + sample_interval_sec)
                t_str = f"{AudioTranscriptionEngine._format_timestamp(t_sec)} - {AudioTranscriptionEngine._format_timestamp(t_end)}"
                visual_text = kf["ocr_text"] or f"Visual scene segment at {t_str}"
                
                all_texts.append(visual_text)
                entities = entity_extractor.extract_entities(visual_text)

                pages.append({
                    "page_num": idx,
                    "text_blocks": [visual_text],
                    "elements": [
                        {
                            "type": "video_segment",
                            "id": str(uuid.uuid4()),
                            "text": visual_text,
                            "start_time": t_sec,
                            "end_time": t_end,
                            "timestamp_str": t_str,
                            "confidence": 1.0,
                            "entities": entities
                        }
                    ],
                    "metadata": {
                        "duration_seconds": duration_sec,
                        "fps": fps,
                        "start_time": t_sec,
                        "end_time": t_end,
                        "timestamp_str": t_str
                    }
                })

        cdo = CommonDocumentObject(
            document_id=document_id,
            fingerprint=fingerprint,
            modality="video",
            filename=filename,
            mime_type=file_metadata.get("mime_type", "video/mp4"),
            classification=classification,
            pages=pages,
            metadata={
                "duration_seconds": duration_sec,
                "fps": fps,
                "total_frames": total_frames,
                "segment_count": len(pages),
                "keyframe_count": len(keyframes),
                "full_transcript": "\n".join(all_texts)
            }
        )
        return cdo
