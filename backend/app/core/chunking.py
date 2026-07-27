import logging
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

# Check if LangChain is available on the local system
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter as LangChainSplitter
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    logger.warning("LangChain not installed. Using NativeRecursiveCharacterTextSplitter fallback.")

class NativeRecursiveCharacterTextSplitter:
    """A zero-dependency Python implementation of Recursive Character Splitting.
    
    Splits text recursively using paragraph, line, and word delimiters to meet size constraints.
    """
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separators: list = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> list:
        return self._split_text(text, self.separators)

    def _split_text(self, text: str, separators: list) -> list:
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # If no separators are left, split strictly by length
            chunks = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunks.append(text[i:i + self.chunk_size])
            return chunks

        separator = separators[0]
        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)

        chunks = []
        current_doc = []
        current_len = 0

        for split in splits:
            if len(split) > self.chunk_size:
                # Flush current accumulator
                if current_doc:
                    chunks.append(separator.join(current_doc))
                    current_doc = []
                    current_len = 0
                
                # Recursively split the oversized fragment using the next level separator
                sub_splits = self._split_text(split, separators[1:])
                chunks.extend(sub_splits)
            else:
                sep_len = len(separator) if current_doc else 0
                if current_len + sep_len + len(split) > self.chunk_size:
                    if current_doc:
                        chunks.append(separator.join(current_doc))
                    
                    # Backtrack to maintain overlap
                    overlap_doc = []
                    overlap_len = 0
                    for item in reversed(current_doc):
                        item_sep_len = len(separator) if overlap_doc else 0
                        if overlap_len + item_sep_len + len(item) <= self.chunk_overlap:
                            overlap_doc.insert(0, item)
                            overlap_len += item_sep_len + len(item)
                        else:
                            break
                    current_doc = overlap_doc
                    current_len = overlap_len
                
                current_doc.append(split)
                current_len += (len(separator) if len(current_doc) > 1 else 0) + len(split)

        if current_doc:
            chunks.append(separator.join(current_doc))

        return chunks

class RecursiveTextSplitter:
    """Delegates splitting logic to LangChain or our native fallback class."""
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if HAS_LANGCHAIN:
            self.splitter = LangChainSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
        else:
            self.splitter = NativeRecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

    def split_text(self, text: str) -> list:
        return self.splitter.split_text(text)

def package_document_chunks(text: str, doc_id: str, source_file: str, dcs: float) -> list:
    """Splits normalized text and packages each segment into a structured dictionary with metadata."""
    splitter = RecursiveTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    raw_chunks = splitter.split_text(text)
    
    packaged = []
    for i, chunk_text in enumerate(raw_chunks):
        packaged.append({
            "chunk_id": f"{doc_id}_chunk_{i}",
            "text": chunk_text,
            "metadata": {
                "document_id": doc_id,
                "source_file": source_file,
                "ocr_confidence": dcs,
                "chunk_index": i
            }
        })
    return packaged
