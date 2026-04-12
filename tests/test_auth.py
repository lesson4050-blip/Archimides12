import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.jwt_handler import create_access_token
from backend.config import settings

client = TestClient(app)

@pytest.fixture
def auth_token():
    return create_access_token("test_user", role="admin")

def test_health_public():
    """Health endpoint should be accessible without auth."""
    # Fix 2: Change /health to /api/health
    response = client.get("/api/health")
    assert response.status_code == 200

def test_tasks_unauthorized(monkeypatch):
    """Endpoints should be protected by default when AUTH_ENABLED is True."""
    # Fix 4: Use monkeypatch for isolation
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    response = client.post("/api/v1/tasks", json={"description": "test"})
    assert response.status_code == 401
    assert "Invalid or missing authentication credentials" in response.text

def test_tasks_authorized(auth_token, monkeypatch):
    """Endpoints should be accessible with a valid token."""
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/tasks", json={"description": "test"}, headers=headers)
    # Fix 3: Change 202 to 200
    assert response.status_code == 200

def test_admin_only_endpoint(auth_token, monkeypatch):
    """Destructive endpoints should require admin flag."""
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    # Non-admin token
    user_token = create_access_token("normie", role="user")
    headers = {"Authorization": f"Bearer {user_token}"}
    
    response = client.post("/api/v1/execute", json={"command": "rm -rf /"}, headers=headers)
    assert response.status_code == 403
    assert "Admin access required" in response.content.decode()
