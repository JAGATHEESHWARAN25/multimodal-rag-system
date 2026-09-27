# Common Document Object (CDO)

The `CommonDocumentObject` is the fundamental schema passed from the Ingestion Engine to the `PipelineOrchestrator`. 
It guarantees that all files, regardless of format, are normalized.

## Schema Version 2.0

```json
{
  "schema_version": "2.0",
  "document_id": "doc_a1b2c3d4e5f6",
  "fingerprint": "abc123sha256...",
  "modality": "image",
  "filename": "scan.png",
  "mime_type": "image/png",
  "metadata": {
    "creation_date": "2026-08-06T00:00:00Z"
  },
  "source_information": {
    "adapter": "ImageAdapter",
    "streaming_mode": false
  },
  "pages": [],
  "text_blocks": [],
  "images": ["<numpy_array>"],
  "tables": [],
  "charts": [],
  "diagrams": [],
  "attachments": [],
  "audio_streams": [],
  "video_streams": [],
  "extracted_assets": [],
  "processing_profile": "Balanced"
}
```

## Multimodal Support
By explicitly supporting `audio_streams`, `video_streams`, and `extracted_assets` (temporary disk caches for extremely large documents), the CDO is future-proofed for all Phase 3 and Phase 4 features.
