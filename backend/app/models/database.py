import sqlite3
import json
import logging
import uuid
from pathlib import Path
from app.config import SQLITE_DB_PATH
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages the centralized SQLite metadata and tracking databases."""
    
    def __init__(self, db_path: Path = SQLITE_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _initialize_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Phase 1.5 - Document Tracking & Fingerprinting Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    sha256_hash TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    mime_type TEXT,
                    modality TEXT,
                    processing_profile TEXT,
                    parent_document_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    schema_json TEXT,
                    owner_id TEXT,
                    classification TEXT DEFAULT 'PUBLIC'
                )
            """)
            
            # Ensure Phase B columns exist in older DBs
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN owner_id TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN classification TEXT DEFAULT 'PUBLIC'")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN summary TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN uploaded_at DATETIME")
                cursor.execute("UPDATE documents SET uploaded_at = created_at WHERE uploaded_at IS NULL")
            except sqlite3.OperationalError:
                pass
            # Phase C migration: Add new columns to audit_logs if they don't exist
            try:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN username TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN event_type TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN resource_type TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN ip_address TEXT")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN request_id TEXT")
                
                # If event_type was just added, backfill it with 'action' for old logs
                cursor.execute("UPDATE audit_logs SET event_type = action WHERE event_type IS NULL")
            except sqlite3.OperationalError:
                pass # Columns already exist

                
            # Phase 1.5 - Processing History Table for Tracing and Benchmarks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    duration_ms INTEGER,
                    model_used TEXT,
                    status TEXT,
                    trace_log TEXT,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                )
            """)
            
            # Phase 1.5 - System Metrics Table for Cache tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    metric_name TEXT PRIMARY KEY,
                    metric_value INTEGER DEFAULT 0
                )
            """)
            
            # Phase 2 Step 6 - Vision Cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_cache (
                    cache_key TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    task TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # --- PHASE A SCHEMA MIGRATIONS ---

            # Migration Tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Users and Roles (RBAC)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Persistent Audit Logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    role TEXT,
                    event_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    status TEXT,
                    ip_address TEXT,
                    request_id TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Persistent Chat Memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)

            # SQLite-backed Background Jobs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    status TEXT DEFAULT 'QUEUED',
                    progress REAL DEFAULT 0.0,
                    current_page INTEGER DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    error TEXT,
                    started_at DATETIME,
                    completed_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                )
            """)

            # Persistent Knowledge Graph (Canonical Source)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_objects (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    parent_id TEXT,
                    object_type TEXT NOT NULL,
                    content TEXT,
                    bounding_box TEXT,
                    metadata_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationship_edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_id) REFERENCES knowledge_objects(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_id) REFERENCES knowledge_objects(id) ON DELETE CASCADE
                )
            """)

            # Create indexing for rapid querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sha256 ON documents(sha256_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_doc ON processing_history(document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_cache ON vision_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bg_job_doc ON background_jobs(document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ko_doc ON knowledge_objects(document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON relationship_edges(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON relationship_edges(target_id)")
            
            # Apply initial version
            cursor.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (1)")
            
            conn.commit()

    def get_document_by_hash(self, sha256_hash: str):
        """Fetches document metadata by hash to implement Level 1 duplicate detection."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE sha256_hash = ?", (sha256_hash,))
            return cursor.fetchone()

    @staticmethod
    def get_all_images():
        """Lists metadata for all uploaded documents in the database registry."""
        with db_manager._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
            
    @staticmethod
    def get_image(document_id: str):
        with db_manager._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_image(document_id: str) -> bool:
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def get_document_summary(document_id: str):
        """Fetches persisted summary for a document if cached."""
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT summary FROM documents WHERE id = ?", (document_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
            return None

    @staticmethod
    def save_document_summary(document_id: str, summary: str):
        """Persists the generated global summary in SQLite for caching."""
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET summary = ? WHERE id = ?", (summary, document_id))
            conn.commit()


    def get_all_users(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role, created_at FROM users")
            return cursor.fetchall()

    def create_user(self, user_id, username, password_hash, role):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, username, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, password_hash, role))
            conn.commit()

    def delete_user(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def update_user_password(self, user_id, new_password_hash):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
            conn.commit()

    def save_document(self, doc_data: dict):
        modality = doc_data.get('modality')
        filename = doc_data.get('filename') or ''
        if not modality or modality == 'unknown':
            existing = self.get_image(doc_data.get('id', ''))
            if existing and existing.get('modality') and existing.get('modality') != 'unknown':
                modality = existing.get('modality')
            else:
                ext = filename.split('.')[-1].lower() if '.' in filename else ''
                if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                    modality = "image"
                elif ext in ["wav", "mp3", "ogg", "m4a", "flac"]:
                    modality = "audio"
                elif ext in ["pdf", "docx", "pptx", "csv", "xlsx", "txt"]:
                    modality = ext
                else:
                    modality = "unknown"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents 
                (id, sha256_hash, filename, mime_type, modality, processing_profile, parent_document_id, status, schema_json, owner_id, classification)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_data.get('id'), doc_data.get('sha256_hash'), filename,
                doc_data.get('mime_type'), modality, doc_data.get('processing_profile'),
                doc_data.get('parent_document_id'), doc_data.get('status', 'processing'),
                doc_data.get('schema_json'), doc_data.get('owner_id'), doc_data.get('classification', 'PUBLIC')
            ))
            conn.commit()

    def create_background_job(self, document_id: str, priority: int = 0) -> str:
        job_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO background_jobs (id, document_id, status)
                VALUES (?, ?, 'QUEUED')
            """, (job_id, document_id))
            conn.commit()
        return job_id

    def get_queued_jobs(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM background_jobs WHERE status = 'QUEUED' ORDER BY created_at ASC")
            return [dict(row) for row in cursor.fetchall()]

    def recover_stale_jobs(self, stale_seconds: int = 300) -> int:
        """Resets jobs stuck in PROCESSING state for more than stale_seconds back to QUEUED."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE background_jobs
                SET status = 'QUEUED', error = 'Recovered from stale PROCESSING state'
                WHERE status = 'PROCESSING'
                AND (started_at IS NULL OR (julianday('now') - julianday(started_at)) * 86400 > ?)
            """, (stale_seconds,))
            conn.commit()
            return cursor.rowcount

    def cancel_background_job(self, job_id: str) -> bool:
        """Marks a job as CANCELLED."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE background_jobs SET status = 'CANCELLED' WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_job_status(self, job_id: str, status: str, error: str = None, progress: float = 0.0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status == 'COMPLETED' or status == 'FAILED' or status == 'CANCELLED':
                cursor.execute("""
                    UPDATE background_jobs 
                    SET status = ?, error = ?, progress = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, error, progress, job_id))
            elif status == 'PROCESSING':
                cursor.execute("""
                    UPDATE background_jobs 
                    SET status = ?, error = ?, progress = ?, started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, error, progress, job_id))
            else:
                cursor.execute("""
                    UPDATE background_jobs 
                    SET status = ?, error = ?, progress = ?
                    WHERE id = ?
                """, (status, error, progress, job_id))
            conn.commit()


    def update_document_status(self, document_id: str, status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET status = ? WHERE id = ?", (status, document_id))
            conn.commit()

    def log_processing_event(self, document_id: str, stage: str, start_time: datetime, end_time: datetime, model_used: str, status: str, trace_log: str = ""):
        """Logs an event into the processing_history table."""
        duration_ms = int((end_time - start_time).total_seconds() * 1000) if end_time and start_time else 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processing_history 
                (document_id, stage, start_time, end_time, duration_ms, model_used, status, trace_log)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id, stage, start_time, end_time, duration_ms, model_used, status, trace_log
            ))
            conn.commit()
            
    def increment_metric(self, metric_name: str, value: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO system_metrics (metric_name, metric_value) VALUES (?, 0)", (metric_name,))
            cursor.execute("UPDATE system_metrics SET metric_value = metric_value + ? WHERE metric_name = ?", (value, metric_name))
            conn.commit()

    def get_vision_cache(self, cache_key: str):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT result_json FROM vision_cache WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def save_vision_cache(self, cache_key: str, document_id: str, engine: str, task: str, result_json: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO vision_cache 
                (cache_key, document_id, engine, task, result_json)
                VALUES (?, ?, ?, ?, ?)
            """, (cache_key, document_id, engine, task, result_json))
            conn.commit()

    def log_audit_event(
        self,
        event_type: str,
        action: str,
        user_id: str = None,
        username: str = None,
        role: str = None,
        resource_type: str = None,
        resource_id: str = None,
        status: str = None,
        ip_address: str = None,
        request_id: str = None,
        details: str = None
    ):
        """Logs an event into the audit_logs table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs 
                (user_id, username, role, event_type, action, resource_type, resource_id, status, ip_address, request_id, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, role, event_type, action, resource_type, resource_id, status, ip_address, request_id, details))
            conn.commit()

    # --- Chat Memory ---
    
    def create_chat_session(self, session_id: str, user_id: str, title: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_sessions (id, user_id, title)
                VALUES (?, ?, ?)
            """, (session_id, user_id, title))
            conn.commit()
            
    def get_chat_sessions(self, user_id: str):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
            return [dict(r) for r in cursor.fetchall()]
            
    def get_chat_session(self, session_id: str, user_id: str):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def update_chat_session_title(self, session_id: str, title: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (title, session_id))
            conn.commit()

    def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
            
    def add_chat_message(self, message_id: str, session_id: str, role: str, content: str, citations_json: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (id, session_id, role, content, citations_json)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, session_id, role, content, citations_json))
            # Update session timestamp
            cursor.execute("UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
            conn.commit()

    def get_chat_messages(self, session_id: str):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
            return [dict(r) for r in cursor.fetchall()]

    def save_knowledge_objects(self, objects: list):
        """Idempotently saves KnowledgeObjects into SQLite knowledge_objects table."""
        if not objects:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for obj in objects:
                obj_id = obj.get("knowledge_object_id") or obj.get("id") or str(uuid.uuid4())
                doc_id = obj.get("parent_document_id") or obj.get("document_id") or ""
                parent_id = obj.get("parent_object_id") or obj.get("parent_id")
                obj_type = obj.get("block_type") or obj.get("object_type") or "unknown"
                content = obj.get("content", "")
                bbox = json.dumps(obj.get("bounding_box")) if obj.get("bounding_box") is not None else None
                meta = json.dumps(obj.get("metadata", {}))

                cursor.execute("""
                    INSERT OR REPLACE INTO knowledge_objects 
                    (id, document_id, parent_id, object_type, content, bounding_box, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (obj_id, doc_id, parent_id, obj_type, content, bbox, meta))
            conn.commit()

    def save_relationship_edges(self, edges: list):
        """Idempotently saves RelationshipEdges into SQLite relationship_edges table."""
        if not edges:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for edge in edges:
                edge_id = edge.get("id") or str(uuid.uuid4())
                source_id = edge.get("source_id", "")
                target_id = edge.get("target_id", "")
                rel_type = edge.get("relationship_type", "CONNECTED_TO")

                cursor.execute("""
                    INSERT OR REPLACE INTO relationship_edges 
                    (id, source_id, target_id, relationship_type)
                    VALUES (?, ?, ?, ?)
                """, (edge_id, source_id, target_id, rel_type))
            conn.commit()

    def get_knowledge_objects_by_document(self, document_id: str) -> list:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_objects WHERE document_id = ?", (document_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if d.get("metadata_json"):
                    try:
                        d["metadata"] = json.loads(d["metadata_json"])
                    except Exception:
                        pass
                if d.get("bounding_box"):
                    try:
                        d["bounding_box"] = json.loads(d["bounding_box"])
                    except Exception:
                        pass
                results.append(d)
            return results

# Singleton
db_manager = DatabaseManager()

