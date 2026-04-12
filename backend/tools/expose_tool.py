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

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "expose",
                "description": "Exposes a port to the public internet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "port": {"type": "integer", "description": "The port number to expose"},
                        "action": {"type": "string", "description": "Optional action"},
                        "path": {"type": "string", "description": "Optional path"}
                    },
                    "required": ["port"]
                }
            }
        }

    async def execute(self, session_id: str = None, port: int = None, action: str = None, path: str = None, **kwargs) -> Dict[str, Any]:
        import re as _re
        if port is None and path:
            match = _re.search(r':(\d+)', path)
            if match:
                port = int(match.group(1))
        if port is None and path:
            # try extracting just digits
            digits = _re.findall(r'\d{4,5}', path)
            if digits:
                port = int(digits[-1])
        if port is None:
            return {"success": False, "error": "port is required"}
        try:
            # Kill any existing tunnel inside the container
            await self.executor.run_command(session_id, "pkill -f 'nokey@localhost.run'")

            # Start SSH tunnel inside the sandbox in background
            ssh_cmd = f"nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:localhost:{port} nokey@localhost.run > /tmp/tunnel_{port}.log 2>&1 &"
            await self.executor.run_command(session_id, ssh_cmd)

            # Read log file for up to 15 seconds to capture the public URL
            url = None
            deadline = asyncio.get_running_loop().time() + 15
            while asyncio.get_running_loop().time() < deadline:
                cat_res = await self.executor.run_command(session_id, f"cat /tmp/tunnel_{port}.log")
                if cat_res.get("success"):
                    line_str = cat_res.get("output", "")
                    match = _re.search(r"https?://[a-zA-Z0-9\-]+\.lhr\.life", line_str)
                    if match:
                        url = match.group(0)
                        break
                await asyncio.sleep(2)

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
