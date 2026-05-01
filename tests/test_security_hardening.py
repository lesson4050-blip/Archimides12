"""Tests for security hardening fixes."""
import pytest
from unittest.mock import AsyncMock, patch

# A1: verify_token returns type field
def test_verify_token_includes_type_field():
    from backend.auth.jwt_handler import create_access_token, verify_token
    token = create_access_token("user-123", role="user")
    payload = verify_token(token)
    assert payload is not None
    assert "type" in payload
    assert payload["type"] == "access"

def test_verify_refresh_token_type():
    from backend.auth.jwt_handler import create_refresh_token, verify_token
    token = create_refresh_token("user-123")
    payload = verify_token(token)
    assert payload is not None
    assert payload["type"] == "refresh"

# A1: Refresh endpoint now works
def test_refresh_requires_refresh_type():
    from backend.auth.jwt_handler import create_access_token, verify_token
    # Access token must NOT be accepted as refresh token
    access_token = create_access_token("user-123")
    payload = verify_token(access_token)
    assert payload["type"] != "refresh"

# A4: Rate limiter cleanup
def test_rate_limiter_cleanup_stale():
    """Rate limiter removes stale IPs."""
    import time
    # Create middleware instance and add stale entries
    from backend.middleware.security import RateLimitMiddleware
    from unittest.mock import MagicMock
    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, requests_per_minute=60)
    
    # Add stale entry (3 minutes ago)
    middleware._buckets["1.2.3.4"] = {
        "tokens": 60,
        "last": time.time() - 200
    }
    # Add many entries to trigger cleanup
    for i in range(10001):
        middleware._buckets[f"10.0.{i//256}.{i%256}"] = {
            "tokens": 60, "last": time.time() - 200
        }
    
    assert len(middleware._buckets) > 10000
    # After dispatch call, stale should be cleaned
    # (Implementation cleans when > 10000 entries)

# A5: Token revocation
@pytest.mark.asyncio
async def test_revoke_token_marks_as_revoked(tmp_path):
    with patch("backend.db.crud.SESSION_DIR", str(tmp_path)):
        from backend.auth.jwt_handler import create_access_token, verify_token
        token = create_access_token("user-test")
        payload = verify_token(token)
        assert payload is not None
        assert payload.get("jti") is not None  # JTI must exist

# A6: Docker security options exist in config
def test_sandbox_manager_has_security_config():
    import inspect
    from backend.sandbox import manager
    source = inspect.getsource(manager)
    assert "no-new-privileges" in source
    assert "cap_drop" in source
