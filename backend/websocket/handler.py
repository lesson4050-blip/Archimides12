import json
import logging
import asyncio
from typing import Dict, List, Any
from fastapi import WebSocket, WebSocketDisconnect
from backend.agent.core import ArchimedesCosmoAgent
from backend.agent.agent_profiles import get_profile
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
        self.agent_loops: Dict[str, ArchimedesCosmoAgent] = {}
        self.buffers: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        
        # Optional auth: verify JWT from query param if AUTH_ENABLED
        if settings.AUTH_ENABLED:
            from backend.auth.jwt_handler import verify_token
            token = websocket.query_params.get("token", "")
            if not token:
                await websocket.send_json({"type": "auth_error", "message": "Authentication required. Pass ?token=JWT"})
                await websocket.close(code=4001)
                return
            payload = verify_token(token)
            if not payload:
                await websocket.send_json({"type": "auth_error", "message": "Invalid or expired token"})
                await websocket.close(code=4001)
                return
            logger.info(f"WebSocket authenticated: user={payload['user_id']} session={session_id}")
        
        self.active_connections[session_id] = websocket
        
        # Flush offline buffer
        if session_id in self.buffers:
            for event in self.buffers[session_id]:
                try:
                    await websocket.send_json(event)
                except Exception:
                    pass
            self.buffers[session_id].clear()

        # --- Manus lifecycle: create container on WS connect ---
        if sandbox_manager.active_session_count >= settings.SANDBOX_MAX_CONTAINERS:
            # At capacity — notify client they are queued
            await websocket.send_json({"type": "session_queued", "message": "All sandbox slots are in use. You are in the queue."})

        success = await sandbox_manager.create_session(session_id)

        if success:
            await websocket.send_json({"type": "session_ready", "message": "Sandbox container is ready."})
            
            # Send novnc_ready
            novnc_url = sandbox_manager.get_novnc_url(session_id)
            if novnc_url:
                await websocket.send_json({"type": "novnc_ready", "url": novnc_url, "success": True})
        else:
            await websocket.send_json({"type": "agent_error", "message": "Failed to create sandbox container."})

        if session_id not in self.agent_loops:
            self.agent_loops[session_id] = ArchimedesCosmoAgent(name="Archimedes COSMO", session_id=session_id)

        logger.info(f"WebSocket connected for session: {session_id}")

    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

        # Do NOT destroy container immediately on disconnect for reconnect resilience.
        # It will be reaped by SandboxManager's reaper task after inactivity timeout.
        
        # We also DON'T clean up agent loop here so it can continue working in the background.

        logger.info(f"WebSocket disconnected for session: {session_id}. Keeping agent and container alive.")

    async def send_event(self, session_id: str, event: Dict[str, Any]):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(event)
            except Exception as e:
                logger.error(f"Error sending event to {session_id}: {e}")
                self._buffer_event(session_id, event)
        else:
            self._buffer_event(session_id, event)

    def _buffer_event(self, session_id: str, event: Dict[str, Any]):
        if session_id not in self.buffers:
            self.buffers[session_id] = []
        self.buffers[session_id].append(event)

    async def handle_message(self, session_id: str, message: str):
        """
        Main entry point for user messages via WebSocket.
        """
        # Touch session on every message to reset inactivity timer
        sandbox_manager.touch_session(session_id)

        logger.info(f"Received WebSocket message for {session_id}: {message}")
        data = json.loads(message)
        task = data.get("task")
        agent_profile_id = data.get("agent_id", "archimedes-cosmo")
        
        if data.get("type") == "set_persona":
            persona_desc = data.get("persona", "")
            agent = self.agent_loops.get(session_id)
            if agent:
                prefix = await agent.persona_mode.build_system_prefix(
                    persona_desc, agent.router
                )
                agent.history[0]["content"] = prefix + "\n\n" + agent.system_prompt
                await self.send_event(session_id, {
                    "type": "persona_activated", 
                    "persona": persona_desc
                })
            return
            
        if not task:
            await self.send_event(session_id, {"type": "agent_error", "message": "No task provided."})
            return

        agent = self.agent_loops.get(session_id)
        if agent:
            # Update agent profile based on frontend selection
            profile = get_profile(agent_profile_id)
            agent.name = profile["name"]
            
            logger.info(f"Starting COSMO agent '{agent.name}' for {session_id} with task: {task}")
            
            # Re-send novnc_ready because the frontend ComputerPanel only mounts after the first task
            novnc_url = sandbox_manager.get_novnc_url(session_id)
            if novnc_url:
                await self.send_event(session_id, {"type": "novnc_ready", "url": novnc_url, "success": True})
            
            async def sender(event):
                await self.send_event(session_id, event)

            # Extra execution parameters (mode: fast/planning)
            mode = data.get("mode", "planning")
            asyncio.create_task(agent.process_task(task, websocket_send=sender, mode=mode))
        else:
            logger.warning(f"No agent found for {session_id}")


manager = ConnectionManager()
