import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.jwt_handler import create_access_token
from backend.config import settings

client = TestClient(app)

@pytest.fixture
def auth_token():
    return create_access_token({"user_id": "test_user", "is_admin": True})

def test_health_public():
    """Health endpoint should be accessible without auth."""
    response = client.get("/health")
    assert response.status_code == 200

def test_tasks_unauthorized():
    """Endpoints should be protected by default when AUTH_ENABLED is True."""
    # Force auth enabled for test
    settings.AUTH_ENABLED = True
    response = client.post("/api/v1/tasks", json={"task": "test"})
    assert response.status_code == 401
    assert "Not authenticated" in response.text

def test_tasks_authorized(auth_token):
    """Endpoints should be accessible with a valid token."""
    settings.AUTH_ENABLED = True
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/tasks", json={"task": "test"}, headers=headers)
    # 202 because task creation is async/queued
    assert response.status_code == 202

def test_admin_only_endpoint(auth_token):
    """Destructive endpoints should require admin flag."""
    settings.AUTH_ENABLED = True
    # Non-admin token
    user_token = create_access_token({"user_id": "normie", "is_admin": False})
    headers = {"Authorization": f"Bearer {user_token}"}
    
    response = client.post("/api/v1/execute", json={"command": "rm -rf /"}, headers=headers)
    assert response.status_code == 403
    assert "Admin privileges required" in response.text
