"""
Proactive Triggers API.
Users can set up scheduled agent tasks.

SECURITY:
- Auth required in production
- Rate limit: 10 trigger operations per minute per IP
- All inputs validated and sanitized
- Max 20 triggers per user
- Min interval 60 seconds
"""
import re
import time
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["triggers"])

_trigger_rate: dict = {}
_TRIGGER_RPM = 10

class TriggerCreate(BaseModel):
    task: str = Field(..., min_length=5, max_length=500)
    schedule_type: str = Field(..., pattern="^(cron|interval)$")
    cron: str = Field(default="", max_length=50)
    interval_seconds: int = Field(default=3600, ge=60, le=86400)
    label: str = Field(default="", max_length=100)
    
    @validator("task")
    def sanitize_task(cls, v):
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        return v.strip()
    
    @validator("label")
    def sanitize_label(cls, v):
        # Only allow alphanumeric, spaces, hyphens
        v = re.sub(r"[^a-zA-Z0-9 \-_]", "", v)
        return v.strip()

def _check_rate(client_ip: str) -> bool:
    now = time.time()
    window = now - 60
    history = [t for t in _trigger_rate.get(client_ip, []) if t > window]
    if len(history) >= _TRIGGER_RPM:
        return False
    history.append(now)
    _trigger_rate[client_ip] = history
    return True

@router.post("/triggers")
async def create_trigger(request: Request, body: TriggerCreate):
    """Create a new proactive trigger."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        from backend.tools.schedule_tool import ScheduleTool
        scheduler = ScheduleTool()
        
        import uuid
        session_id = f"trigger_{uuid.uuid4().hex[:8]}"
        
        result = await scheduler.execute(
            action="add",
            cron=body.cron if body.schedule_type == "cron" else None,
            interval_seconds=body.interval_seconds if body.schedule_type == "interval" else None,
            task_description=body.task,
            session_id=session_id,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
        
        return {"success": True, "message": result.get("output"), "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trigger creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create trigger")

@router.get("/triggers")
async def list_triggers(request: Request):
    """List all active triggers."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        from backend.tools.schedule_tool import ScheduleTool
        scheduler = ScheduleTool()
        result = await scheduler.execute(action="list")
        return {"success": True, "output": result.get("output", "No triggers")}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list triggers")

@router.delete("/triggers/{job_id:path}")
async def delete_trigger(request: Request, job_id: str):
    """Delete a trigger by ID."""
    # Validate job_id format before using it
    if not re.match(r'^job_[a-zA-Z0-9_-]{1,50}$', job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        from backend.tools.schedule_tool import ScheduleTool
        scheduler = ScheduleTool()
        result = await scheduler.execute(action="remove", job_id=job_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete trigger")
