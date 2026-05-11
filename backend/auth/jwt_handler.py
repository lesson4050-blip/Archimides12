"""
JWT token management and API key generation for Archimedes Auth.
Uses python-jose for JWT and secrets for API keys.
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from backend.config import settings

logger = logging.getLogger(__name__)


def create_access_token(user_id: str, role: str = "user", extra: dict = None) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    }
    if extra:
        payload.update(extra)
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.info(f"JWT access token created for user {user_id} (role={role}, expires={settings.JWT_EXPIRATION_HOURS}h)")
    return token


def create_refresh_token(user_id: str, role: str = "user") -> str:
    """Create a JWT refresh token."""
    payload = {
        "sub": user_id,
        "role": role,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=7),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.info(f"JWT refresh token created for user {user_id} (expires=7d)")
    return token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    Returns decoded payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return {
            "user_id": user_id,
            "role": payload.get("role", "user"),
            "exp": payload.get("exp"),
            "type": payload.get("type"),
            "jti": payload.get("jti"),
        }
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def create_api_key() -> str:
    """Generate a secure 64-character hex API key."""
    return secrets.token_hex(32)

import bcrypt
import hashlib

def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage. Never store raw keys."""
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Constant-time comparison of API key hash."""
    import hmac
    return hmac.compare_digest(
        hash_api_key(raw_key),
        hashed_key
    )

def hash_password(password: str) -> str:
    """Hash password using bcrypt with SHA-256 pre-hash (handles passwords > 72 bytes)."""
    # SHA-256 pre-hash prevents bcrypt 72-byte truncation vulnerability
    password_bytes = hashlib.sha256(password.encode('utf-8')).digest()
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash. Constant-time comparison."""
    password_bytes = hashlib.sha256(plain_password.encode('utf-8')).digest()
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False
