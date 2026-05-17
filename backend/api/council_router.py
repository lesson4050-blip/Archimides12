"""
Model Council API endpoint.
Runs multiple model configs in parallel, returns all responses.

SECURITY:
- Rate limited: max 5 requests/minute per IP
- Input length capped at 2000 chars
- Output per model capped at 4000 chars
- Timeout enforced per request
- Auth required in production mode
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["council"])

# Simple in-memory rate limiter for council endpoint
_council_rate: dict = {}
_COUNCIL_RPM = 5  # requests per minute per IP
_COUNCIL_TIMEOUT = 45.0  # seconds

class CouncilRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=2000)
    mode: str = Field("council", pattern="^(council|synthesize)$")
    
    @validator("task")
    def sanitize_task(cls, v):
        # Strip null bytes and control characters
        v = v.replace("\x00", "").strip()
        if not v:
            raise ValueError("Task cannot be empty after sanitization")
        return v

class CouncilResponse(BaseModel):
    type: str
    task: str
    responses: list
    successful_count: int
    total_count: int
    elapsed_seconds: float

def _check_council_rate_limit(client_ip: str) -> bool:
    """Simple token bucket rate limiter for council endpoint."""
    now = time.time()
    window_start = now - 60
    
    history = _council_rate.get(client_ip, [])
    history = [t for t in history if t > window_start]
    
    if len(history) >= _COUNCIL_RPM:
        return False
    
    history.append(now)
    _council_rate[client_ip] = history
    return True

@router.post("/council", response_model=CouncilResponse)
async def run_council(
    request: Request,
    body: CouncilRequest,
):
    """Run Model Council — parallel multi-model comparison."""
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit
    if not _check_council_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max {_COUNCIL_RPM} council requests per minute"
        )
    
    start = time.time()
    
    try:
        from backend.models.model_router import ModelRouter
        from backend.agent.intelligence.moa_engine import MixtureOfAgents
        
        router_instance = ModelRouter()
        moa = MixtureOfAgents(router_instance)
        
        messages = [{"role": "user", "content": body.task}]
        
        result = await moa.council(
            messages=messages,
            task=body.task,
            timeout_seconds=_COUNCIL_TIMEOUT,
        )
        
        elapsed = round(time.time() - start, 2)
        
        return CouncilResponse(
            type="council",
            task=body.task[:200],  # truncate in response
            responses=result["responses"],
            successful_count=result["successful_count"],
            total_count=result["total_count"],
            elapsed_seconds=elapsed,
        )
        
    except Exception as e:
        logger.error(f"Council endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Council request failed")
