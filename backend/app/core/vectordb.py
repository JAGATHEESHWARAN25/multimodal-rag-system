import logging
import json
import sqlite3
import numpy as np
from pathlib import Path
from app.config import CHROMA_DIR, SQLITE_DIR

logger = logging.getLogger(__name__)

# State variables for ChromaDB imports
_HAS_CHROMA = False
try:
    import chromadb
    from chromadb.config import Settings
    _HAS_CHROMA = True
except ImportError:
    logger.warning("chromadb library not installed. Vector DB pipeline will run NativeSQLiteVectorStore fallback.")

class NativeSQLiteVectorStore:
    """A zero-dependency local vector store database.
    
    Persists document chunks and embedding floats inside an SQLite database and computes
    cosine similarity rankings natively in Python.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT,
                collection_name TEXT,
                text TEXT,
                metadata_json TEXT,
                embedding_json TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_col ON vector_chunks (collection_name, document_id)")
        conn.commit()
        conn.close()

    def add_documents(self, collection_name: str, ids: list, embeddings: list, documents: list, metadatas: list):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for chunk_id, embedding, doc, meta in zip(ids, embeddings, documents, metadatas):
            doc_id = meta.get("document_id", "")
            cursor.execute(
                """
                INSERT OR REPLACE INTO vector_chunks 
                (chunk_id, document_id, collection_name, text, metadata_json, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chunk_id, doc_id, collection_name, doc, json.dumps(meta), json.dumps(embedding))
            )
        conn.commit()
        conn.close()

    def query_similarity(self, collection_name: str, query_embedding: list, limit: int = 5, filter_document_ids: list = None) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if filter_document_ids:
            placeholders = ",".join(["?"] * len(filter_document_ids))
            cursor.execute(
                f"SELECT chunk_id, text, metadata_json, embedding_json FROM vector_chunks WHERE collection_name = ? AND document_id IN ({placeholders})",
                [collection_name] + list(filter_document_ids)
            )
        else:
            cursor.execute(
                "SELECT chunk_id, text, metadata_json, embedding_json FROM vector_chunks WHERE collection_name = ?",
                (collection_name,)
            )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            q_norm = 1.0

        matches = []
        for chunk_id, text, meta_json, embed_json in rows:
            vec = np.array(json.loads(embed_json), dtype=np.float32)
            
            # Align dimension if vector was created with a previous embedding model
            if vec.shape[0] != q_vec.shape[0]:
                if vec.shape[0] < q_vec.shape[0]:
                    vec = np.pad(vec, (0, q_vec.shape[0] - vec.shape[0]), 'constant')
                else:
                    vec = vec[:q_vec.shape[0]]

            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                vec_norm = 1.0
                
            # Cosine similarity calculation
            cosine_score = float(np.dot(q_vec, vec) / (q_norm * vec_norm))
            
            # Convert cosine similarity to distance representation:
            # Chroma uses L2/cosine distance where smaller means closer.
            # distance = 1.0 - similarity.
            distance = 1.0 - cosine_score
            
            matches.append({
                "id": chunk_id,
                "document": text,
                "metadata": json.loads(meta_json),
                "distance": distance
            })

        # Sort matches by distance ascending (closest first)
        matches = sorted(matches, key=lambda x: x["distance"])[:limit]

        return {
            "ids": [m["id"] for m in matches],
            "documents": [m["document"] for m in matches],
            "metadatas": [m["metadata"] for m in matches],
            "distances": [m["distance"] for m in matches]
        }

    def delete_by_document(self, collection_name: str, document_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM vector_chunks WHERE collection_name = ? AND document_id = ?",
            (collection_name, document_id)
        )
        conn.commit()
        conn.close()

    def purge_orphaned_chunks(self, valid_document_ids: list):
        """Removes vector chunks belonging to deleted or invalid document IDs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if valid_document_ids:
            placeholders = ",".join(["?"] * len(valid_document_ids))
            cursor.execute(
                f"DELETE FROM vector_chunks WHERE document_id NOT IN ({placeholders}) OR document_id IS NULL OR document_id = ''",
                list(valid_document_ids)
            )
        else:
            cursor.execute("DELETE FROM vector_chunks")
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Purged {deleted_count} orphaned vector chunks from vector store.")
        return deleted_count


class VectorDatabaseManager:
    """Managespersistent client connections to ChromaDB or SQLite vector indices."""
    
    _CLIENT = None
    _SQLITE_STORE = None

    @classmethod
    def get_client(cls):
        if _HAS_CHROMA:
            if cls._CLIENT is not None:
                return cls._CLIENT
            try:
                CHROMA_DIR.mkdir(parents=True, exist_ok=True)
                cls._CLIENT = chromadb.PersistentClient(path=str(CHROMA_DIR))
                logger.info(f"Persistent ChromaDB Client connected successfully at '{CHROMA_DIR}'")
                return cls._CLIENT
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB Persistent Client. Error: {str(e)}")
                
        # Connect to Native SQLite Store if ChromaDB fails to initialize or is missing
        if cls._SQLITE_STORE is None:
            db_file = SQLITE_DIR / "vector_index.db"
            logger.info(f"Initializing fallback Local SQLite Vector Database at '{db_file}'")
            cls._SQLITE_STORE = NativeSQLiteVectorStore(db_file)
            
        return cls._SQLITE_STORE

    @classmethod
    def index_document_chunks(cls, collection_name: str, chunks: list, embeddings: list):
        """Indexes a list of document chunks alongside their corresponding embeddings."""
        if not chunks:
            return
            
        client = cls.get_client()
        ids = [chunk["chunk_id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        if isinstance(client, NativeSQLiteVectorStore):
            client.add_documents(collection_name, ids, embeddings, texts, metadatas)
        else:
            try:
                collection = client.get_or_create_collection(name=collection_name)
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
            except Exception as e:
                logger.error(f"ChromaDB insert failed. Switching to SQLite fallback. Error: {str(e)}")
                # Fail-safe write to SQLite DB
                fallback_db = SQLITE_DIR / "vector_index.db"
                store = NativeSQLiteVectorStore(fallback_db)
                store.add_documents(collection_name, ids, embeddings, texts, metadatas)

    @classmethod
    def semantic_query(cls, collection_name: str, query_embedding: list, query_text: str = "", limit: int = 5, filter_document_ids: list = None) -> list:
        """Retrieves matching document chunk segments using semantic similarities, optionally filtered by document IDs."""
        client = cls.get_client()
        
        # Fetch a larger pool of candidates to ensure hybrid search can boost documents with lower dense scores
        fetch_limit = limit * 5
        
        if isinstance(client, NativeSQLiteVectorStore):
            results_list = []
            results = client.query_similarity(collection_name, query_embedding, fetch_limit, filter_document_ids=filter_document_ids)
            if results and results.get("ids"):
                for i in range(len(results["ids"])):
                    results_list.append({
                        "chunk_id": results["ids"][i],
                        "text": results["documents"][i],
                        "metadata": results["metadatas"][i],
                        "score": 1.0 - results["distances"][i]
                    })
        else:
            results_list = []
            try:
                collection = client.get_collection(name=collection_name)
                query_kwargs = {
                    "query_embeddings": [query_embedding],
                    "n_results": fetch_limit
                }
                if filter_document_ids:
                    if len(filter_document_ids) == 1:
                        query_kwargs["where"] = {"document_id": filter_document_ids[0]}
                    else:
                        query_kwargs["where"] = {"document_id": {"$in": filter_document_ids}}
                raw_results = collection.query(**query_kwargs)
                if raw_results and raw_results.get("ids") and raw_results["ids"][0]:
                    for i in range(len(raw_results["ids"][0])):
                        results_list.append({
                            "chunk_id": raw_results["ids"][0][i],
                            "text": raw_results["documents"][0][i],
                            "metadata": raw_results["metadatas"][0][i],
                            "score": 1.0 - (raw_results["distances"][0][i] / 2.0)
                        })
            except Exception as e:
                logger.error(f"ChromaDB query failed: {e}")
                
            try:
                fallback_db = SQLITE_DIR / "vector_index.db"
                if fallback_db.exists():
                    store = NativeSQLiteVectorStore(fallback_db)
                    fallback_results = store.query_similarity(collection_name, query_embedding, fetch_limit, filter_document_ids=filter_document_ids)
                    if fallback_results and fallback_results.get("ids"):
                        for i in range(len(fallback_results["ids"])):
                            results_list.append({
                                "chunk_id": fallback_results["ids"][i],
                                "text": fallback_results["documents"][i],
                                "metadata": fallback_results["metadatas"][i],
                                "score": 1.0 - fallback_results["distances"][i]
                            })
            except Exception as e:
                logger.error(f"SQLite Fallback query failed: {e}")
                
        matches = []
        seen_docs = set()
        
        # Pre-process query keywords for hybrid search boost
        import re
        query_words = set(re.findall(r'\b\w{4,}\b', query_text.lower()))
        
        for r in results_list:
            similarity_score = max(0.0, min(1.0, r["score"]))
            
            # Hybrid Search Boost
            text_lower = r["text"].lower()
            keyword_matches = sum(1 for w in query_words if w in text_lower)
            if keyword_matches > 0:
                similarity_score = min(1.0, similarity_score + (keyword_matches * 0.10))
                
            chunk_id = r["chunk_id"]
            if similarity_score >= 0.20 and chunk_id not in seen_docs:
                seen_docs.add(chunk_id)
                matches.append({
                    "chunk_id": chunk_id,
                    "text": r["text"],
                    "score": round(similarity_score, 4),
                    "metadata": r["metadata"]
                })
                
        matches = sorted(matches, key=lambda x: x["score"], reverse=True)
        return matches[:limit]

    @classmethod
    def delete_document_indices(cls, collection_name: str, document_id: str):
        """Removes all indexed chunk elements matching a document ID."""
        client = cls.get_client()
        if isinstance(client, NativeSQLiteVectorStore):
            client.delete_by_document(collection_name, document_id)
        else:
            try:
                collection = client.get_collection(name=collection_name)
                collection.delete(where={"document_id": document_id})
            except Exception as e:
                logger.error(f"ChromaDB delete indices failed: {str(e)}")
                # Clean from SQL store just in case
                fallback_db = SQLITE_DIR / "vector_index.db"
                store = NativeSQLiteVectorStore(fallback_db)
                store.delete_by_document(collection_name, document_id)

    @classmethod
    def purge_orphaned_chunks(cls, valid_document_ids: list):
        """Removes vector chunks not matching any active document in SQLite metadata."""
        fallback_db = SQLITE_DIR / "vector_index.db"
        if fallback_db.exists():
            store = NativeSQLiteVectorStore(fallback_db)
            return store.purge_orphaned_chunks(valid_document_ids)
        return 0
