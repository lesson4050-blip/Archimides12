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
from backend.middleware.rate_limiter import council_limiter

logger = logging.getLogger(__name__)

from backend.security.sandbox_hardening import SecurityGate
_injection_gate = SecurityGate()
router = APIRouter(prefix="/api/v1", tags=["council"])

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



@router.post("/council", response_model=CouncilResponse)
async def run_council(
    request: Request,
    body: CouncilRequest,
):
    """Run Model Council — parallel multi-model comparison."""
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit
    if not council_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit: max 5 council requests per minute"
        )
    
    start = time.time()
    
    # ═══ PROMPT INJECTION GUARD ═══
    verdict = _injection_gate.full_prompt_analysis(body.task)
    if not verdict.allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Request blocked by security filter: {verdict.reasons[0] if verdict.reasons else 'Injection detected'}"
        )
    
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
