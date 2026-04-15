import uuid
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from backend.presentation.schemas import TaskStatus
from backend.presentation.pipeline import PresentationPipeline, save_task_state, get_task_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/presentation", tags=["Presentation"])

# Simple dependency injection
pipeline = PresentationPipeline()

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Topic or prompt for the presentation")
    theme_id: str = Field("tech-blue", description="Theme ID (e.g. tech-blue, minimal-dark, creative-gradient)")

@router.post("/generate", response_model=TaskStatus)
async def generate_presentation(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Initiates the Gamma-level presentation generation pipeline in the background.
    Returns a TaskStatus object containing the task_id immediately.
    """
    task_id = uuid.uuid4().hex
    
    task_status = TaskStatus(
        task_id=task_id,
        status="pending",
        progress=0.0
    )
    
    save_task_state(task_status)
    
    # Schedule the background task (does NOT block the event loop)
    background_tasks.add_task(
        pipeline.generate_background,
        task_id=task_id,
        prompt=request.prompt,
        theme_id=request.theme_id
    )
    
    logger.info(f"Scheduled presentation generation task: {task_id}")
    return task_status

@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    Returns the current progress and status of a generation task.
    """
    task_status = get_task_state(task_id)
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return task_status
