import os
import sys
from pathlib import Path
import uuid

# Add the backend path to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.database import db_manager
from app.core.security import get_password_hash, Role

def seed_users():
    seed_data = [
        {"username": "admin", "password": "password123", "role": Role.SYSTEM_ADMIN},
        {"username": "analyst", "password": "password123", "role": Role.INTELLIGENCE_ANALYST},
        {"username": "officer", "password": "password123", "role": Role.DOCUMENT_OFFICER},
        {"username": "reviewer", "password": "password123", "role": Role.REVIEWER},
        {"username": "viewer", "password": "password123", "role": Role.VIEWER},
    ]

    with db_manager._get_connection() as conn:
        cursor = conn.cursor()
        for user in seed_data:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (user["username"],))
            existing = cursor.fetchone()
            if not existing:
                hashed = get_password_hash(user["password"])
                user_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT OR IGNORE INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                    (user_id, user["username"], hashed, user["role"].value)
                )
                print(f"Seeded user: {user['username']} ({user['role'].value})")
        conn.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_users()
