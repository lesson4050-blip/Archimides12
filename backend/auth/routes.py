"""
Auth API routes: registration, login, API key management.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
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
from backend.auth.dependencies import get_current_user, require_admin
from backend.db.crud import AsyncSessionLocal
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Request/Response Models ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    expires_in_hours: int


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
        
        new_user = User(
            id=user_id,
            email=request.email,
            hashed_password=hashed,
            role="admin" if await _is_first_user(db) else "user",
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
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
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
        
        logger.info(f"User logged in: {user.email}")
        
        return LoginResponse(
            access_token=token,
            user_id=user.id,
            role=user.role,
            expires_in_hours=settings.JWT_EXPIRATION_HOURS,
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    if current_user.get("auth_method") == "dev-bypass":
        return UserResponse(
            id="dev-user",
            email="dev@archimedes.local",
            role="admin",
            is_active=True,
            created_at=datetime.utcnow().isoformat(),
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
        
        user.api_key = new_key
        await db.commit()
    
    logger.info(f"API key generated for user {current_user['user_id']}")
    
    return APIKeyResponse(
        api_key=new_key,
        message="Save this key securely — it will not be shown again.",
    )


async def _is_first_user(db) -> bool:
    """Check if this is the first user being registered (gets admin role)."""
    result = await db.execute(select(User).limit(1))
    return result.scalar_one_or_none() is None
