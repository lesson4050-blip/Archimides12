import logging
import asyncio
import os
import io
import tarfile
from typing import Dict, Any
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
        Starts Xvfb, x11vnc, and websockify inside the container using a single script.
        """
        logger.info(f"Starting desktop streaming for session {session_id}...")
        
        container = await self.executor.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Container not found"}

        # Copy browser_server.py to container
        server_path = os.path.join(os.path.dirname(__file__), "browser_server.py")
        if os.path.exists(server_path):
            with open(server_path, "rb") as f:
                tar_stream = io.BytesIO()
                with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                    tar_add_info = tarfile.TarInfo(name="browser_server.py")
                    content = f.read()
                    tar_add_info.size = len(content)
                    tar.addfile(tar_add_info, io.BytesIO(content))
                tar_stream.seek(0)
                container.put_archive("/home/ubuntu/workspace", tar_stream)

        # Create a single startup script for the UI
        startup_script = f"""#!/bin/bash
export DISPLAY=:1
Xvfb :1 -screen 0 1280x720x24 &
sleep 1
openbox &
xterm -geometry 150x50+10+10 -bg '#312b3e' -fg white -title 'Archimedes Sandbox' -e "echo Archimedes Session Started; date; bash" &
python3 /home/ubuntu/workspace/browser_server.py &
x11vnc -display :1 -nopw -forever -shared -rfbport 5900 -bg
/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen {port}
"""
        # Securely write script directly via put_archive
        tar_script_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_script_stream, mode='w') as tar:
            script_bytes = startup_script.encode('utf-8')
            tar_add_info = tarfile.TarInfo(name="start_ui.sh")
            tar_add_info.size = len(script_bytes)
            # Make the file fully executable
            tar_add_info.mode = 0o755  
            tar.addfile(tar_add_info, io.BytesIO(script_bytes))
        tar_script_stream.seek(0)
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: container.put_archive("/home/ubuntu", tar_script_stream))

        # Run the script in DETACHED mode so processes persist
        await self.executor.run_command(session_id, "/home/ubuntu/start_ui.sh", detach=True)
        
        # Give it a moment to boot
        await asyncio.sleep(2)
            
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
