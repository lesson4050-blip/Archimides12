"""
Quick Task Router — lightweight single-shot endpoint for VS Code extension.
No session, no memory, fast turnaround.
"""
import time
import logging
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

from backend.security.sandbox_hardening import SecurityGate
_injection_gate = SecurityGate()

router = APIRouter(prefix="/api/v1", tags=["quick"])

# ── Simple in-memory rate limiter ────────────────────────────────
_rate_store: dict = defaultdict(list)  # ip -> [timestamps]
_RATE_LIMIT = 30  # requests per minute
_RATE_WINDOW = 60  # seconds


def _check_rate_limit(client_id: str = "default") -> bool:
    """Returns True if within limits, False if exceeded."""
    now = time.time()
    _rate_store[client_id] = [
        t for t in _rate_store[client_id] if now - t < _RATE_WINDOW
    ]
    if len(_rate_store[client_id]) >= _RATE_LIMIT:
        return False
    _rate_store[client_id].append(now)
    return True


# ── Request / Response models ────────────────────────────────────

class QuickTaskRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=10000)
    stream: bool = False
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    @field_validator("task")
    @classmethod
    def task_not_empty(cls, v):
        stripped = v.strip()
        if not stripped:
            raise ValueError("Task cannot be empty or whitespace-only")
        return stripped


class QuickTaskResponse(BaseModel):
    result: str
    model: str | None = None
    latency_ms: int = 0


# ── Endpoint ─────────────────────────────────────────────────────

from fastapi import Request as FastAPIRequest

@router.post("/quick-task", response_model=QuickTaskResponse)
async def quick_task(req: QuickTaskRequest, request: FastAPIRequest):
    """
    Lightweight single-shot task execution for VS Code extension.
    No session, no memory, just fast answer.
    """
    # Rate limiting
    client_ip = request.client.host if request.client else "default"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 30 requests/minute."
        )

    t0 = time.time()

    # ═══ PROMPT INJECTION GUARD ═══
    verdict = _injection_gate.full_prompt_analysis(req.task)
    if not verdict.allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Request blocked by security filter: {verdict.reasons[0] if verdict.reasons else 'Injection detected'}"
        )

    try:
        from backend.models.model_router import ModelRouter
        from backend.agent.intelligence.cot_engine import inject_cot

        router_inst = ModelRouter()
        messages = inject_cot(
            [{"role": "user", "content": req.task}], req.task
        )
        resp = await router_inst.generate(
            messages=messages,
            task_hint="fast",
            temperature=req.temperature,
        )

        latency = int((time.time() - t0) * 1000)
        result_text = resp.get("text", "")

        if not result_text:
            raise HTTPException(
                status_code=502,
                detail="Model returned empty response"
            )

        logger.info(f"QuickTask completed in {latency}ms (model={resp.get('model')})")

        return QuickTaskResponse(
            result=result_text,
            model=resp.get("model"),
            latency_ms=latency,
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"QuickTask import error: {e}")
        raise HTTPException(status_code=500, detail=f"Backend module not found: {e}")
    except Exception as e:
        logger.error(f"QuickTask failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {type(e).__name__}")
