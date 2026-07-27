import sqlite3
import datetime
from pathlib import Path
from app.config import SQLITE_DB_PATH

class DatabaseManager:
    """Manages the SQLite database connection, table initialization, and CRUD operations."""

    @classmethod
    def get_connection(cls):
        """Returns a connection to the SQLite database with row factory enabled."""
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def initialize_db(cls):
        """Creates the required tables if they do not exist."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        # Create 'images' table to registry documents and status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                storage_path TEXT NOT NULL UNIQUE,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    @classmethod
    def add_image(cls, image_id: str, filename: str, storage_path: str, file_size: int, mime_type: str) -> dict:
        """Inserts a new image record into the database."""
        upload_time = datetime.datetime.utcnow().isoformat()
        status = "Uploaded"
        
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO images (id, filename, storage_path, file_size, mime_type, upload_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (image_id, filename, str(storage_path), file_size, mime_type, upload_time, status)
        )
        conn.commit()
        conn.close()
        
        return {
            "id": image_id,
            "filename": filename,
            "size_bytes": file_size,
            "upload_time": upload_time,
            "status": status
        }

    @classmethod
    def get_all_images(cls) -> list:
        """Returns metadata for all registered images."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, file_size, mime_type, upload_time, status FROM images ORDER BY upload_time DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "filename": row["filename"],
                "size_bytes": row["file_size"],
                "mime_type": row["mime_type"],
                "upload_time": row["upload_time"],
                "status": row["status"]
            }
            for row in rows
        ]

    @classmethod
    def get_image(cls, image_id: str) -> dict:
        """Retrieves a single image record by its ID."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, storage_path, file_size, mime_type, upload_time, status FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "filename": row["filename"],
                "storage_path": row["storage_path"],
                "size_bytes": row["file_size"],
                "mime_type": row["mime_type"],
                "upload_time": row["upload_time"],
                "status": row["status"]
            }
        return None

    @classmethod
    def delete_image(cls, image_id: str) -> bool:
        """Deletes an image record from the database. Returns True if deleted, False otherwise."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
