"""
SSE Streaming endpoint — connects model-level streaming to HTTP API.

Uses Server-Sent Events (SSE) for real-time token streaming.
Clients connect via POST /api/v1/stream/task to start a streaming task.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream", tags=["streaming"])

# Active streams registry
_active_streams: Dict[str, asyncio.Queue] = {}


class StreamTaskRequest(BaseModel):
    """Request to start a streaming task."""
    description: str = Field(..., min_length=1, max_length=50_000)
    mode: str = Field(default="auto", pattern=r"^(auto|planning|codeact|single)$")
    session_id: Optional[str] = Field(default=None, max_length=100)


async def _sse_generator(
    queue: asyncio.Queue, task_id: str
) -> AsyncGenerator[str, None]:
    """Generate SSE events from a queue."""
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
            except asyncio.TimeoutError:
                yield f"event: ping\ndata: {{}}\n\n"
                continue

            if event is None:
                yield f"event: done\ndata: {json.dumps({'task_id': task_id})}\n\n"
                break

            event_type = event.get("type", "token")
            yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _active_streams.pop(task_id, None)


@router.post("/task")
async def stream_task(
    request: StreamTaskRequest,
    user: dict = Depends(get_current_user),
):
    """Start a task with SSE streaming response."""
    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _active_streams[task_id] = queue

    from backend.models.model_router import get_model_router
    from backend.agent.tool_registry import ToolRegistry
    from backend.memory.context_manager import ContextManager
    from backend.agent.orchestration.orchestrator import AgentOrchestrator

    model_router = get_model_router()
    tool_registry = ToolRegistry()
    context_manager = ContextManager(model_router)
    orchestrator = AgentOrchestrator(model_router, tool_registry, context_manager)

    async def queue_send(event: Dict[str, Any]):
        """Callback to bridge orchestrator events to SSE queue."""
        await queue.put(event)

    async def run_task():
        try:
            await queue.put({
                "type": "start",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            result = await orchestrator.run_task(
                task_description=request.description,
                session_id=request.session_id or task_id,
                websocket_send=queue_send,  # Pass bridge callback
                stream=True,
            )

            await queue.put({
                "type": "result",
                "task_id": task_id,
                "data": {
                    "response": result.get("output", ""),
                    "status": "completed" if result.get("success") else "failed",
                },
            })
        except Exception as e:
            logger.error(f"Stream task error: {e}")
            await queue.put({
                "type": "error",
                "task_id": task_id,
                "error": str(e),
            })
        finally:
            await queue.put(None)

    asyncio.create_task(run_task())

    return StreamingResponse(
        _sse_generator(queue, task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Task-Id": task_id,
        },
    )


@router.get("/status")
async def stream_status(user: dict = Depends(get_current_user)):
    """Get active streams count."""
    return {
        "active_streams": len(_active_streams),
        "stream_ids": list(_active_streams.keys()),
    }
