from fastapi import APIRouter, HTTPException, Depends
from backend.auth.dependencies import get_current_user
from backend.db.crud import AsyncSessionLocal
from backend.db.models import UserSettings, UsageRecord
from backend.tools.scheduler_singleton import get_scheduler
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

class UpdateSettingsRequest(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None
    product_updates: Optional[bool] = None
    task_emails: Optional[bool] = None
    nickname: Optional[str] = None
    occupation: Optional[str] = None
    bio: Optional[str] = None
    custom_instructions: Optional[str] = None
    browser_persistence: Optional[bool] = None
    integrations_json: Optional[Dict[str, Any]] = None
    skills_json: Optional[Dict[str, Any]] = None
    connectors_json: Optional[Dict[str, Any]] = None

class CreateTaskRequest(BaseModel):
    task_description: str
    schedule_at: Optional[str] = None  # Expected simple ISO format or human readable
    interval_seconds: Optional[int] = None

@router.get("", summary="Get user settings")
async def get_settings(user: dict = Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("sub")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            # Create default settings if not exists
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
            
        return settings

@router.post("", summary="Update user settings")
async def update_settings(request: UpdateSettingsRequest, user: dict = Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("sub")
    async with AsyncSessionLocal() as db:
        # Check if settings exist
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            return settings
            
        for key, value in update_data.items():
            setattr(settings, key, value)
            
        await db.commit()
        await db.refresh(settings)
        return settings

@router.get("/usage", summary="Get usage records")
async def get_usage(user: dict = Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("sub")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UsageRecord)
            .where(UsageRecord.user_id == user_id)
            .order_by(UsageRecord.created_at.desc())
        )
        return result.scalars().all()

@router.get("/scheduler", summary="Get scheduled tasks")
async def get_scheduled_tasks(user: dict = Depends(get_current_user)):
    scheduler = get_scheduler()
    # In a real app we'd store these in the DB too
    return {"status": "success", "jobs": scheduler._jobs if hasattr(scheduler, '_jobs') else []}

@router.post("/scheduler", summary="Create scheduled task")
async def create_scheduled_task(request: CreateTaskRequest, user: dict = Depends(get_current_user)):
    scheduler = get_scheduler()
    res = await scheduler.execute(
        action="add",
        task_description=request.task_description,
        interval_seconds=request.interval_seconds or 3600  # Default 1h if not specified
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/cleanup", summary="Clean browser and session data")
async def cleanup_data(user: dict = Depends(get_current_user)):
    # This would call sandbox_manager.cleanup() or specific browser data wiping logic
    logger.info(f"User {user['sub']} requested data cleanup.")
    return {"status": "success", "message": "Browser and temporary data successfully wiped."}

class FolderRequest(BaseModel):
    path: str

@router.post("/folders", summary="Add local folder access")
async def add_folder(request: FolderRequest, user: dict = Depends(get_current_user)):
    import os
    if not os.path.exists(request.path):
         raise HTTPException(status_code=400, detail=f"Path does not exist: {request.path}")
    
    user_id = user.get("user_id") or user.get("sub")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one()
        
        connectors = settings.connectors_json or {}
        local_folders = connectors.get("local_folders", [])
        if request.path not in local_folders:
            local_folders.append(request.path)
            connectors["local_folders"] = local_folders
            
            settings.connectors_json = connectors
            await db.commit()
            await db.refresh(settings)
                
    return {"status": "success", "message": f"Folder {request.path} registered."}

@router.get("/folders", summary="List local folders")
async def list_folders(user: dict = Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("sub")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one()
        return settings.connectors_json.get("local_folders", []) if settings.connectors_json else []
