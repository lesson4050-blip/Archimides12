import asyncio
import logging
import re
from typing import Dict, Any
from backend.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)

class ExposeTool:
    """
    Exposes a sandbox port to a public URL using localhost.run (free, no signup).
    """
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor
        self._tunnels: Dict[int, asyncio.subprocess.Process] = {}

    async def execute(self, session_id: str, port: int, **kwargs) -> Dict[str, Any]:
        try:
            # Kill any existing tunnel for this port
            if port in self._tunnels:
                try:
                    self._tunnels[port].terminate()
                except Exception:
                    pass

            # Start SSH tunnel to localhost.run in background
            proc = await asyncio.create_subprocess_exec(
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-R", f"80:localhost:{port}",
                "nokey@localhost.run",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            self._tunnels[port] = proc

            # Read output for up to 15 seconds to capture the public URL
            url = None
            deadline = asyncio.get_event_loop().time() + 15
            while asyncio.get_event_loop().time() < deadline:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=2)
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    logger.info(f"localhost.run: {line_str}")
                    match = re.search(r"https?://[a-zA-Z0-9\-]+\.lhr\.life", line_str)
                    if match:
                        url = match.group(0)
                        break
                except asyncio.TimeoutError:
                    continue

            if url:
                return {
                    "success": True,
                    "url": url,
                    "output": f"Port {port} is now publicly accessible at {url}"
                }
            else:
                return {
                    "success": False,
                    "error": "Could not obtain public URL from localhost.run within 15 seconds. Make sure the sandbox has internet access and SSH is available."
                }

        except Exception as e:
            logger.error(f"ExposeTool error: {e}")
            return {"success": False, "error": str(e)}
