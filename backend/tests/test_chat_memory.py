import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import db_manager

client = TestClient(app)

def test_chat_session_lifecycle():
    # 1. Create a session
    resp = client.post("/api/chat/sessions", json={"title": "Test Chat"})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    session_id = data["id"]
    
    # 2. List sessions
    resp = client.get("/api/chat/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert any(s["id"] == session_id for s in sessions)
    
    # Let's just check the API structure for get and delete
    resp = client.get(f"/api/chat/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session"]["title"] == "Test Chat"
    
    # Delete
    resp = client.delete(f"/api/chat/sessions/{session_id}")
    assert resp.status_code == 200
    
    # Verify deletion
    resp = client.get(f"/api/chat/sessions/{session_id}")
    assert resp.status_code == 404

def test_chat_session_isolation():
    # Create as admin (globally mocked)
    resp = client.post("/api/chat/sessions", json={"title": "Admin Secret Chat"})
    session_id = resp.json()["id"]
    
    # Change mock to viewer
    from app.core.security import get_current_user, UserContext, Role
    app.dependency_overrides[get_current_user] = lambda: UserContext(id="viewer_id", username="viewer", role=Role.VIEWER)
    
    try:
        # Try to read as viewer
        resp = client.get(f"/api/chat/sessions/{session_id}")
        assert resp.status_code == 404
        
        # Try to delete as viewer
        resp = client.delete(f"/api/chat/sessions/{session_id}")
        assert resp.status_code == 404
    finally:
        # Restore default mock
        from tests.conftest import mock_get_current_user
        app.dependency_overrides[get_current_user] = mock_get_current_user
