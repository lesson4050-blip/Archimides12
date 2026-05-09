"""
Auth API routes: registration, login, API key management.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from backend.config import settings
from backend.auth.jwt_handler import (
    create_access_token,
    create_api_key,
    hash_password,
    verify_password,
)
from backend.auth.dependencies import get_current_user
from backend.db.crud import AsyncSessionLocal
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Request/Response Models ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str = "Authenticated successfully. Tokens set in HttpOnly cookies."
    user_id: str
    role: str
    expires_in_hours: int

class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    has_api_key: bool


class APIKeyResponse(BaseModel):
    api_key: str
    message: str


# ── Endpoints ──

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new user account."""
    async with AsyncSessionLocal() as db:
        # Check if email already exists
        existing = await db.execute(select(User).where(User.email == request.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        user_id = str(uuid.uuid4())
        hashed = hash_password(request.password)
        
        # Atomic first-user check using advisory locks to prevent race
        from sqlalchemy import func, text
        
        # Serialize concurrent registrations at DB level (PostgreSQL)
        try:
            await db.execute(text("SELECT pg_advisory_xact_lock(12345)"))
        except Exception:
            pass # SQLite doesn't support this, but it serializes writes anyway
        
        user_count_result = await db.execute(
            select(func.count()).select_from(User)
        )
        user_count = user_count_result.scalar()
        is_first = (user_count == 0)

        new_user = User(
            id=user_id,
            email=request.email,
            hashed_password=hashed,
            role="admin" if is_first else "user",
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"New user registered: {request.email} (role={new_user.role})")
        
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            role=new_user.role,
            is_active=new_user.is_active,
            created_at=new_user.created_at.isoformat(),
            has_api_key=bool(new_user.api_key),
        )


@router.post("/login", response_model=LoginResponse)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with email/password. Returns JWT access token.
    Uses OAuth2 form format: username=email, password=password.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == form_data.username))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        
        token = create_access_token(user.id, user.role)
        from backend.auth.jwt_handler import create_refresh_token
        refresh_token = create_refresh_token(user.id, user.role)
        
        logger.info(f"User logged in: {user.email}")
        
        # Set HttpOnly cookies
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.JWT_EXPIRATION_HOURS * 3600
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.JWT_EXPIRATION_HOURS * 3600 * 24 * 7 # 7 days
        )
        
        return LoginResponse(
            user_id=user.id,
            role=user.role,
            expires_in_hours=settings.JWT_EXPIRATION_HOURS,
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_access_token(request_data: RefreshRequest, request: Request, response: Response):
    """Refresh access token using refresh token from cookie or body."""
    from backend.auth.jwt_handler import verify_token, create_access_token, create_refresh_token
    from backend.db.crud import revoke_token, is_token_revoked

    token_to_verify = request.cookies.get("refresh_token") or request_data.refresh_token
    payload = verify_token(token_to_verify)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check JTI-based revocation (prevents replay of old refresh tokens)
    old_jti = payload.get("jti")
    if old_jti and await is_token_revoked(old_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == payload["user_id"]))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Revoke the OLD refresh token so it cannot be replayed
        if old_jti and payload.get("exp"):
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            await revoke_token(jti=old_jti, user_id=user.id, expires_at=expires_at)

        new_access = create_access_token(user.id, user.role)
        new_refresh = create_refresh_token(user.id, user.role)
        
        response.set_cookie(
            key="access_token",
            value=new_access,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.JWT_EXPIRATION_HOURS * 3600
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.JWT_EXPIRATION_HOURS * 3600 * 24 * 7
        )
        
        return LoginResponse(
            user_id=user.id,
            role=user.role,
            expires_in_hours=settings.JWT_EXPIRATION_HOURS,
        )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user — clears cookies AND revokes JWT tokens (both in-memory and DB)."""
    from backend.auth.token_blacklist import blacklist
    from backend.auth.jwt_handler import verify_token
    from backend.db.crud import revoke_token

    # Revoke the access token if present
    token = request.cookies.get("access_token")
    if token:
        payload = verify_token(token)
        if payload and payload.get("exp"):
            await blacklist.revoke(token, payload["exp"])
            # Persist JTI revocation to DB (survives server restarts)
            if payload.get("jti"):
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                await revoke_token(
                    jti=payload["jti"],
                    user_id=payload["user_id"],
                    expires_at=expires_at,
                )

    # Revoke the refresh token if present
    refresh = request.cookies.get("refresh_token")
    if refresh:
        payload = verify_token(refresh)
        if payload and payload.get("exp"):
            await blacklist.revoke(refresh, payload["exp"])
            # Persist JTI revocation to DB
            if payload.get("jti"):
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                await revoke_token(
                    jti=payload["jti"],
                    user_id=payload["user_id"],
                    expires_at=expires_at,
                )

    response.delete_cookie(
        key="access_token", httponly=True, secure=True, samesite="lax"
    )
    response.delete_cookie(
        key="refresh_token", httponly=True, secure=True, samesite="lax"
    )
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    if current_user.get("auth_method") == "dev-bypass":
        return UserResponse(
            id="dev-user",
            email="dev@archimedes.local",
            role="admin",
            is_active=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            has_api_key=False,
        )
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == current_user["user_id"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            has_api_key=bool(user.api_key),
        )


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_api_key(current_user: dict = Depends(get_current_user)):
    """Generate a new API key for the authenticated user. Replaces any existing key."""
    if current_user.get("auth_method") == "dev-bypass":
        raise HTTPException(status_code=400, detail="Enable AUTH_ENABLED to use API keys")
    
    new_key = create_api_key()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == current_user["user_id"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        from backend.auth.jwt_handler import hash_api_key
        user.api_key = hash_api_key(new_key)
        await db.commit()
    
    logger.info(f"API key generated for user {current_user['user_id']}")
    
    return APIKeyResponse(
        api_key=new_key,
        message="Save this key securely — it will not be shown again.",
    )

