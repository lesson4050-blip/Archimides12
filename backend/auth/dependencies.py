"""
FastAPI dependency injection for authentication.
Supports both JWT Bearer tokens and X-API-Key header.
When AUTH_ENABLED=False, all requests pass through (dev mode).
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, Header, status, Request
from fastapi.security import OAuth2PasswordBearer

from backend.config import settings
from backend.auth.jwt_handler import verify_token

logger = logging.getLogger(__name__)

# OAuth2 scheme — extracts Bearer token from Authorization header
# auto_error=False so we can fall through to API key check
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> dict:
    """
    Authenticate the current user via JWT token OR API key.
    
    When AUTH_ENABLED=False (dev mode), returns a default dev user.
    When AUTH_ENABLED=True, requires valid JWT or API key.
    
    Returns dict with: user_id, role, auth_method
    """
    # Dev mode — skip auth entirely
    if not settings.AUTH_ENABLED:
        return {
            "user_id": "dev-user",
            "role": "admin",
            "auth_method": "dev-bypass",
        }
    
    # Try JWT token first (from header or cookie)
    jwt_token = token or request.cookies.get("access_token")
    if jwt_token:
        payload = verify_token(jwt_token)
        if payload:
            # Check raw-token blacklist
            from backend.auth.token_blacklist import blacklist
            if await blacklist.is_revoked(jwt_token):
                pass  # Fall through to API key check or 401
            else:
                # Check JTI-based revocation (database)
                jti = payload.get("jti")
                if jti:
                    from backend.db.crud import is_token_revoked
                    if await is_token_revoked(jti):
                        pass  # Fall through — token was revoked
                    else:
                        return {
                            "user_id": payload["user_id"],
                            "role": payload["role"],
                            "auth_method": "jwt",
                        }
                else:
                    # Legacy tokens without JTI — allow through
                    return {
                        "user_id": payload["user_id"],
                        "role": payload["role"],
                        "auth_method": "jwt",
                    }
    
    # Try API key
    if x_api_key:
        user = await _lookup_user_by_api_key(x_api_key)
        if user:
            return {
                "user_id": user["id"],
                "role": user["role"],
                "auth_method": "api_key",
            }
    
    # No valid auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[dict]:
    """
    Like get_current_user but returns None instead of raising 401.
    Used for endpoints that work both authenticated and anonymously.
    """
    try:
        return await get_current_user(request, token, x_api_key)
    except HTTPException:
        return None


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


import time

import asyncio

_API_KEY_CACHE: dict = {}
_API_KEY_LOCKS: dict = {}
_API_KEY_LOCKS_LOCK = asyncio.Lock()  # protects _API_KEY_LOCKS itself

async def _lookup_user_by_api_key(api_key: str) -> Optional[dict]:
    """Look up a user by their API key in the database (with 5-minute TTL cache)."""
    now = time.time()
    from backend.auth.jwt_handler import hash_api_key
    hashed_key = hash_api_key(api_key)
    
    # Fast path — cache hit (no lock needed for reads)
    cached = _API_KEY_CACHE.get(hashed_key)
    if cached and now < cached["exp"]:
        return cached["user"]
    
    # Slow path — need DB lookup, use per-key lock to prevent stampede
    async with _API_KEY_LOCKS_LOCK:
        if hashed_key not in _API_KEY_LOCKS:
            _API_KEY_LOCKS[hashed_key] = asyncio.Lock()
        key_lock = _API_KEY_LOCKS[hashed_key]
    
    async with key_lock:
        # Double-check after acquiring lock
        cached = _API_KEY_CACHE.get(hashed_key)
        if cached and now < cached["exp"]:
            return cached["user"]
        
        # Cleanup stale entries
        stale = [k for k, v in list(_API_KEY_CACHE.items()) if v["exp"] < now]
        for k in stale:
            del _API_KEY_CACHE[k]
            _API_KEY_LOCKS.pop(k, None)
        
        # DB lookup
        try:
            from sqlalchemy import select
            from backend.db.crud import AsyncSessionLocal
            from backend.db.models import User
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(
                        User.api_key == hashed_key,
                        User.is_active.is_(True)
                    )
                )
                user = result.scalar_one_or_none()
                if user:
                    user_data = {"id": user.id, "role": user.role, "email": user.email}
                    _API_KEY_CACHE[hashed_key] = {"user": user_data, "exp": now + 300}
                    return user_data
        except Exception as e:
            logger.error(f"API key lookup failed: {e}")
        return None
