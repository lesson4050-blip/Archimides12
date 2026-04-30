from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

@router.get(\"/stream\")
async def stream_tokens(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected(): break
            yield f\"data: {json.dumps({'token': '...'})}\\n\\n\"
            await asyncio.sleep(0.1)
    return StreamingResponse(event_generator(), media_type=\"text/event-stream\")
