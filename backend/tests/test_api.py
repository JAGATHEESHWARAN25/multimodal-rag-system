import pytest
from fastapi.testclient import TestClient
import numpy as np
import cv2
import uuid
import io

# We need to import the app. If app/main.py is not ready for testing, we can mock or start it.
from app.main import app
from app.core.ingestion.adapters.manager import AdapterManager
from app.core.ingestion.adapters.image_adapter import ImageAdapter

client = TestClient(app)

def create_synthetic_image_bytes():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    success, buffer = cv2.imencode(".png", img)
    return buffer.tobytes()

def test_api_upload_image():
    # Ensure adapter is registered for tests
    AdapterManager.register_adapter(["image/png", "image/jpeg"], ImageAdapter)
    
    file_bytes = create_synthetic_image_bytes()
    # The endpoint expects 'files' list
    files_param = [('files', ('test.png', file_bytes, 'image/png'))]
    
    from app.core.security import create_access_token
    token = create_access_token({"sub": "admin_id", "username": "admin", "role": "SYSTEM_ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/api/upload", files=files_param, headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    
    jobs = data
    if jobs:
        job = jobs[0]
        assert "document_id" in job
        assert "job_id" in job
        assert job["filename"] == "test.png"
