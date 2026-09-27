# Adapter Interface

The Adapter Interface defines how all new modalities are introduced into the platform.

## Design Philosophy
Adapters are **dumb extractors**. 
They must NEVER:
- Perform OCR
- Enhance images
- Generate semantic chunks
- Embed text

They ONLY:
- Parse a raw file byte stream.
- Extract embedded assets (text, images, tables).
- Normalize everything into a single `CommonDocumentObject`.

## `BaseAdapter`

```python
class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, file_bytes: bytes, file_metadata: Dict[str, Any]) -> Union[CommonDocumentObject, Generator[CommonDocumentObject, None, None]]:
        pass
```

### Streaming vs In-Memory
If a document is small, `parse()` should return a `CommonDocumentObject`.
If a document is extremely large (e.g., 500-page PDF), the adapter can `yield` a `CommonDocumentObject` for each page. The `IngestionEngine` automatically detects this and routes the stream through the pipeline page-by-page.
