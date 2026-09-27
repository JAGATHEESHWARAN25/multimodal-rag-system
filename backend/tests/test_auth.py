import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import db_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    """Ensure database state is clean between tests."""
    with db_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM vision_cache")
        cursor.execute("DELETE FROM processing_history")
        cursor.execute("DELETE FROM knowledge_objects")
        cursor.execute("DELETE FROM relationship_edges")
        cursor.execute("DELETE FROM audit_logs")
        conn.commit()
    yield
from tests.conftest import mock_get_current_user
from app.core.security import get_current_user

@pytest.fixture(autouse=True)
def clear_overrides():
    """Ensure real authentication is used for these tests, then restore."""
    old_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.update(old_overrides)

def test_login_success():
    # Admin seed user is expected to exist
    response = client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["role"] == "SYSTEM_ADMIN"

def test_login_failure():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401

def test_protected_route_without_token():
    response = client.get("/api/images")
    assert response.status_code == 403 # HTTPBearer raises 403 when no auth is provided

def test_protected_route_with_token():
    token_res = client.post("/api/auth/login", json={"username": "viewer", "password": "password123"})
    token = token_res.json()["access_token"]
    
    response = client.get("/api/images", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_rbac_upload_denied_for_viewer():
    token_res = client.post("/api/auth/login", json={"username": "viewer", "password": "password123"})
    token = token_res.json()["access_token"]
    
    response = client.post("/api/upload", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403 # Missing or invalid files triggers 422 if allowed, but 403 triggers first

def test_rbac_delete_denied_for_officer():
    token_res = client.post("/api/auth/login", json={"username": "officer", "password": "password123"})
    token = token_res.json()["access_token"]
    
    response = client.delete("/api/images/fake-id", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
