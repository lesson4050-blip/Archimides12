"""
FastAPI dependency injection for authentication.
Supports both JWT Bearer tokens and X-API-Key header.
When AUTH_ENABLED=False, all requests pass through (dev mode).
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer

from backend.config import settings
from backend.auth.jwt_handler import verify_token

logger = logging.getLogger(__name__)

# OAuth2 scheme — extracts Bearer token from Authorization header
# auto_error=False so we can fall through to API key check
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
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
    
    # Try JWT token first
    if token:
        payload = verify_token(token)
        if payload:
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
    token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[dict]:
    """
    Like get_current_user but returns None instead of raising 401.
    Used for endpoints that work both authenticated and anonymously.
    """
    try:
        return await get_current_user(token, x_api_key)
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


async def _lookup_user_by_api_key(api_key: str) -> Optional[dict]:
    """Look up a user by their API key in the database."""
    try:
        from sqlalchemy import select
        from backend.db.crud import AsyncSessionLocal
        from backend.db.models import User
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.api_key == api_key, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            if user:
                return {"id": user.id, "role": user.role, "email": user.email}
    except Exception as e:
        logger.error(f"API key lookup failed: {e}")
    return None
