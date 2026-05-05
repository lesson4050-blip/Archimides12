import json
import asyncio
import logging
import socket
from typing import Dict, Any, Optional
from backend.agent.tools.base import BaseTool

logger = logging.getLogger(__name__)

class BrowserTool(BaseTool):
    """
    World-class autonomous browser tool.
    Connects to the browser_server.py inside the sandbox.
    Supports navigation, interaction, and smart extraction.
    """
    
    def __init__(self, sandbox_manager):
        self.sandbox = sandbox_manager
        super().__init__(
            name="browser",
            description="Autonomous browser for web research and UI testing. Actions: navigate, click, type, extract, screenshot."
        )

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string", 
                        "description": "Action to perform: navigate, click, type, type_and_submit, extract, scroll, screenshot, get_elements, get_dom_tree, current_state."
                    },
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "text": {"type": "string", "description": "Text to click or type"},
                    "selector": {"type": "string", "description": "CSS selector for the element"},
                    "query": {"type": "string", "description": "Search query for extraction"},
                    "amount": {"type": "integer", "description": "Scroll amount in pixels"},
                    "direction": {"type": "string", "description": "Scroll direction: up or down"}
                },
                "required": ["action"]
            }
        }

    async def _send_cmd(self, session_id: str, action: str, **kwargs) -> Dict[str, Any]:
        """Sends a JSON command to the browser server via TCP socket."""
        try:
            # Ensure UI is started (this is fast if already running)
            await self.sandbox.novnc.start_streaming(session_id)
            
            # Browser server listens on 9222 inside the container
            # We use docker exec to talk to it via socat or just use the manager's executor
            # Actually, the simplest way is to write to the CMD_FILE (/tmp/browser_cmd.json)
            # as defined in browser_server.py, but TCP is faster.
            # However, since we are on the host, we'll use file IPC for maximum reliability across OSs.
            
            cmd = {"action": action, **kwargs}
            
            # Write command to container
            cmd_json = json.dumps(cmd)
            write_res = await self.sandbox.executor.run_command(
                session_id, 
                f"echo '{cmd_json}' > /tmp/browser_cmd.json"
            )
            
            if not write_res.get("success"):
                return {"success": False, "error": f"Failed to send browser command: {write_res.get('error')}"}
            
            # Poll for result (RES_FILE: /tmp/browser_res.json)
            for _ in range(30): # 15s timeout
                await asyncio.sleep(0.5)
                check_res = await self.sandbox.executor.run_command(session_id, "cat /tmp/browser_res.json")
                if check_res.get("success") and check_res.get("output"):
                    try:
                        result = json.loads(check_res.get("output"))
                        # Clean up result file
                        await self.sandbox.executor.run_command(session_id, "rm /tmp/browser_res.json")
                        return result
                    except:
                        continue
            
            return {"success": False, "error": "Browser command timed out"}
        except Exception as e:
            logger.error(f"BrowserTool error: {e}")
            return {"success": False, "error": str(e)}

    async def execute(self, session_id: str, action: str, **kwargs) -> Dict[str, Any]:
        """
        Actions:
        - navigate(url: str)
        - click(text: str or selector: str)
        - type(selector: str, text: str)
        - extract(query: str)
        """
        logger.info(f"[{session_id}] Browser Action: {action}")
        return await self._send_cmd(session_id, action, **kwargs)
