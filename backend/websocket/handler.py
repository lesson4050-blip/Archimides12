import json
import logging
import asyncio
from typing import Dict, List, Any
from fastapi import WebSocket, WebSocketDisconnect
from backend.agent.core import AgentLoop
from backend.sandbox.singleton import sandbox_manager
from backend.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections.
    Ties container lifecycle to WebSocket sessions (Manus-style).
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_loops: Dict[str, AgentLoop] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

        # --- Manus lifecycle: create container on WS connect ---
        if sandbox_manager.active_session_count >= settings.SANDBOX_MAX_CONTAINERS:
            # At capacity — notify client they are queued
            await websocket.send_json({"type": "session_queued", "message": "All sandbox slots are in use. You are in the queue."})

        success = await sandbox_manager.create_session(session_id)

        if success:
            await websocket.send_json({"type": "session_ready", "message": "Sandbox container is ready."})
        else:
            await websocket.send_json({"type": "agent_error", "message": "Failed to create sandbox container."})

        if session_id not in self.agent_loops:
            self.agent_loops[session_id] = AgentLoop(session_id)

        logger.info(f"WebSocket connected for session: {session_id}")

    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

        # --- Manus lifecycle: destroy container on WS disconnect ---
        await sandbox_manager.destroy_session(session_id)

        # Clean up agent loop
        if session_id in self.agent_loops:
            agent = self.agent_loops[session_id]
            agent.is_running = False
            del self.agent_loops[session_id]

        logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_event(self, session_id: str, event: Dict[str, Any]):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(event)
            except Exception as e:
                logger.error(f"Error sending event to {session_id}: {e}")

    async def handle_message(self, session_id: str, message: str):
        """
        Main entry point for user messages via WebSocket.
        """
        # Touch session on every message to reset inactivity timer
        sandbox_manager.touch_session(session_id)

        logger.info(f"Received WebSocket message for {session_id}: {message}")
        data = json.loads(message)
        task = data.get("task")
        
        if not task:
            await self.send_event(session_id, {"type": "agent_error", "message": "No task provided."})
            return

        agent = self.agent_loops.get(session_id)
        if agent:
            logger.info(f"Starting AgentLoop.run for {session_id} with task: {task}")
            async def sender(event):
                await self.send_event(session_id, event)

            asyncio.create_task(agent.run(task, websocket_send=sender))
        else:
            logger.warning(f"No agent found for {session_id}")


manager = ConnectionManager()
