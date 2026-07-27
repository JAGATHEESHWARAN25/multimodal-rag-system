import logging
import numpy as np
import math
from app.config import EMBEDDINGS_MODEL

logger = logging.getLogger(__name__)

# State variables for our singleton model loader
_EMBEDDINGS_MODEL_INST = None
_IMPORT_SUCCESS = False

try:
    from sentence_transformers import SentenceTransformer
    _IMPORT_SUCCESS = True
except ImportError:
    logger.warning("sentence-transformers not installed. Embedding pipeline will use LocalMathEmbedding fallback.")

class LocalMathEmbedding:
    """A lightweight, zero-dependency TF-IDF style vector fallback.
    
    Generates deterministic 768-dimensional normalized vectors representing text semantics,
    guaranteeing standard vector operations (like cosine similarity) function offline.
    """
    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def encode(self, texts: list) -> np.ndarray:
        """Converts a list of texts into a 2D numpy array of shape (len(texts), 768)."""
        vectors = []
        for text in texts:
            # Generate deterministic values based on character occurrences
            vec = np.zeros(self.dimension, dtype=np.float32)
            
            # Simple term-hashing representation
            words = text.lower().split()
            for w in words:
                # Hash the word to pick a vector index
                idx = sum(ord(c) * (i + 1) for i, c in enumerate(w)) % self.dimension
                vec[idx] += 1.0
                
            # Add a secondary letter n-gram representation
            for i in range(len(text) - 1):
                bigram = text[i:i+2]
                idx = sum(ord(c) * (j + 2) for j, c in enumerate(bigram)) % self.dimension
                vec[idx] += 0.5

            # Apply L2 normalization
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            else:
                vec[0] = 1.0 # default unit vector
                
            vectors.append(vec)
            
        return np.array(vectors, dtype=np.float32)

class LocalEmbeddingsCalculator:
    """Memory-efficient singleton wrapper for offline document embeddings calculations."""
    
    @classmethod
    def get_model(cls):
        global _EMBEDDINGS_MODEL_INST
        if _EMBEDDINGS_MODEL_INST is not None:
            return _EMBEDDINGS_MODEL_INST
            
        import os
        force_mock = os.getenv("FORCE_MOCK_EMBEDDINGS", "false").lower() == "true"
        
        if _IMPORT_SUCCESS and not force_mock:
            try:
                logger.info(f"Loading local SentenceTransformer model: '{EMBEDDINGS_MODEL}'...")
                # Load model locally; if offline and not cached, this will throw an error caught below
                _EMBEDDINGS_MODEL_INST = SentenceTransformer(EMBEDDINGS_MODEL)
                logger.info("SentenceTransformer model loaded successfully.")
                return _EMBEDDINGS_MODEL_INST
            except Exception as e:
                logger.error(
                    f"Failed to download/load SentenceTransformer '{EMBEDDINGS_MODEL}' offline.\n"
                    f"Falling back to LocalMathEmbedding simulator. Error: {str(e)}"
                )
                
        # Fallback to pure math encoder
        _EMBEDDINGS_MODEL_INST = LocalMathEmbedding(dimension=768)
        return _EMBEDDINGS_MODEL_INST

    @classmethod
    def calculate_embeddings(cls, texts: list) -> list:
        """Calculates embeddings for a list of string segments.
        
        Returns a list of 768-dimensional float arrays.
        """
        if not texts:
            return []
            
        model = cls.get_model()
        try:
            # Ensure output is a list of Python lists (not numpy arrays) for easy JSON serializations
            embeddings = model.encode(texts)
            if isinstance(embeddings, np.ndarray):
                return embeddings.tolist()
            return embeddings
        except Exception as e:
            logger.error(f"Error calculating embeddings: {str(e)}")
            # Fail-safe backup
            fallback = LocalMathEmbedding(dimension=768)
            return fallback.encode(texts).tolist()

    @classmethod
    def calculate_query_embedding(cls, query: str) -> list:
        """Calculates the embedding vector for a single query string."""
        embeddings = cls.calculate_embeddings([query])
        return embeddings[0] if embeddings else [0.0] * 768
