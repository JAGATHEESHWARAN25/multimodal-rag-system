import pytest
from app.models.database import db_manager
from app.main import app
from app.core.security import get_current_user, get_current_user_flexible, UserContext, Role
from scripts.seed_users import seed_users
import sqlite3
import os
from pathlib import Path

# Globally mock authentication for integration tests
def mock_get_current_user():
    return UserContext(id="admin_id", username="admin", role=Role.SYSTEM_ADMIN)

app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_current_user_flexible] = mock_get_current_user

@pytest.fixture(autouse=True)
def clean_database():
    """Wipe all tables before every test to ensure test isolation."""
    with db_manager._get_connection() as conn:
        cursor = conn.cursor()
        tables = [
            "documents", "processing_history", "vision_cache", 
            "system_metrics", "schema_migrations", "users", 
            "audit_logs", "chat_sessions", "chat_messages", 
            "background_jobs", "knowledge_objects", "relationship_edges"
        ]
        for t in tables:
            try:
                cursor.execute(f"DELETE FROM {t}")
            except sqlite3.OperationalError:
                pass # Table might not exist yet during some test phases
        conn.commit()
    
    # Re-seed the users since we deleted them
    seed_users()
