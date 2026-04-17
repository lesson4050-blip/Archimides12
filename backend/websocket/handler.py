import logging
import asyncio
from typing import Dict, List, Any
from fastapi import WebSocket
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
            del self.buffers[session_id]

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
            agent = ArchimedesCosmoAgent(name="Archimedes COSMO", session_id=session_id)
            await agent.initialize()
            self.agent_loops[session_id] = agent

        logger.info(f"WebSocket connected for session: {session_id}")

    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if session_id in self.buffers:
            del self.buffers[session_id]

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
        import time
        if not hasattr(self, '_rate_buckets'):
            self._rate_buckets: Dict[str, list] = {}
        now = time.time()
        bucket = [t for t in self._rate_buckets.get(session_id, [])
                  if now - t < 60]
        if len(bucket) >= 15:
            await self.send_event(session_id, {
                "type": "agent_error",
                "message": "Rate limit: 15 tasks/minute. Please wait."
            })
            return
        bucket.append(now)
        self._rate_buckets[session_id] = bucket

        # Touch session on every message to reset inactivity timer
        sandbox_manager.touch_session(session_id)

        logger.info(f"Received WebSocket message for {session_id}: {message}")
        from backend.utils.json_repair import repair_and_parse
        data, err = repair_and_parse(message)
        if data is None:
            logger.error(f"WebSocket: invalid JSON from client: {err}")
            await self.send_event(session_id, {
                "type": "agent_error",
                "message": "Invalid message format."
            })
            return
        if not isinstance(data, dict):
            data = {}
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
            
            # Process UI flags for extra prompt injection
            use_web_search = data.get("use_web_search", False)
            use_globe = data.get("use_globe", False)
            
            base_prompt = profile.get("system_prompt", agent.system_prompt)
            extra_instructions = ""
            
            if use_web_search:
                extra_instructions += "\n\nCRITICAL DIRECTIVE: The user has explicitly enabled Web Search. You MUST use web search tools to find current, up-to-date information before concluding your research."
                
            if use_globe:
                extra_instructions += "\n\nCRITICAL DIRECTIVE: The user has explicitly enabled Internet/Globe context. You are encouraged to use the browser tool and navigate through live web pages if deeper contextual surfing is required."
                
            agent.system_prompt = base_prompt + extra_instructions
            if len(agent.history) > 0 and agent.history[0]["role"] == "system":
                agent.history[0]["content"] = agent.system_prompt
            
            logger.info(f"Starting COSMO agent '{agent.name}' for {session_id} with task: {task} | WebSearch: {use_web_search} | Globe: {use_globe}")
            
            # Re-send novnc_ready because the frontend ComputerPanel only mounts after the first task
            novnc_url = sandbox_manager.get_novnc_url(session_id)
            if novnc_url:
                await self.send_event(session_id, {"type": "novnc_ready", "url": novnc_url, "success": True})
            
            # Enable token streaming for faster perceived response
            async def streaming_sender(event):
                await self.send_event(session_id, event)

            # Extra execution parameters (mode: fast/planning)
            mode_req = data.get("mode", "planning")
            task_hint = data.get("task_hint", "default")
            
            asyncio.create_task(agent.process_task(
                task, 
                websocket_send=streaming_sender, 
                mode=mode_req, 
                task_hint=task_hint,
                stream=True  # Enable streaming
            ))
        else:
            logger.warning(f"No agent found for {session_id}")


manager = ConnectionManager()
