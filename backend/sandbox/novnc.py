import logging
from typing import Dict, Any, Optional
from backend.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)

class NoVNCManager:
    """
    Manages noVNC streaming for the sandbox desktop.
    """
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor

    async def start_streaming(self, session_id: str, port: int = 6080) -> Dict[str, Any]:
        """
        Starts Xvfb, x11vnc, and websockify inside the container.
        """
        logger.info(f"Starting desktop streaming for session {session_id}...")
        
        # 1. Start Xvfb (Display :1)
        # 2. Start Fluxbox (WM)
        # 3. Start x11vnc
        # 4. Start websockify
        
        # We run these as background processes
        cmds = [
            "Xvfb :1 -screen 0 1280x720x24 &",
            "DISPLAY=:1 fluxbox &",
            "DISPLAY=:1 x11vnc -display :1 -nopw -forever -shared -bg &",
            f"/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen {port} &"
        ]
        
        for cmd in cmds:
            # We use & to run in background
            await self.executor.run_command(session_id, cmd)
            
        # The VNC URL will be reachable from the host if we port forward or 
        # just return the proxy URL.
        # Since it's inside Docker, we need the host to communicate.
        # For simplicity, returning the address that the frontend can use.
        # If running locally, it's localhost:6080 (if mapped).
        
        return {
            "success": True, 
            "url": f"http://localhost:{port}/vnc.html?autoconnect=true&reconnect=true",
            "output": "Desktop streaming started successfully."
        }

    async def stop_streaming(self, session_id: str):
        # Kill fluxbox, x11vnc, websockify, Xvfb
        cmd = "pkill fluxbox; pkill x11vnc; pkill websockify; pkill Xvfb"
        await self.executor.run_command(session_id, cmd)
        return {"success": True}
