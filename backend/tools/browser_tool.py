import logging
import json
import asyncio
import shlex
import time
from typing import Dict, Any
from backend.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)

CMD_FILE = "/tmp/browser_cmd.json"
RES_FILE = "/tmp/browser_res.json"
LOCK_FILE = "/tmp/browser_lock"


class BrowserTool:
    """
    Manus-level browser automation.
    Communicates with persistent browser_server.py inside the sandbox.
    """
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": (
                    "Automates a web browser. Navigate to URLs, read page content, "
                    "click elements by their visible text, type into inputs, "
                    "extract specific information, and take screenshots. "
                    "Always use 'navigate' first, then 'extract' to read content."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "navigate",    # Go to URL, returns content + elements
                                "extract",     # Get page text, optionally filtered by query
                                "click",       # Click by visible text or CSS selector
                                "type",        # Type into input field
                                "type_and_submit",  # Type + press Enter
                                "scroll",      # Scroll page
                                "screenshot",  # Take screenshot
                                "get_elements", # List all interactive elements
                                "wait_for",    # Wait for element to appear
                                "current_state" # Get URL/title/elements (no content)
                            ],
                            "description": "Browser action to perform"
                        },
                        "url": {
                            "type": "string",
                            "description": "URL for navigate action"
                        },
                        "text": {
                            "type": "string",
                            "description": "Visible text of element to click, or text to type"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for click/type/wait_for"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search term for extract action - filters content to relevant sections"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["down", "up"],
                            "description": "Scroll direction"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Scroll amount in pixels (default 500)"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Screenshot save path"
                        },
                        "timeout_ms": {
                            "type": "integer",
                            "description": "Timeout for wait_for action in ms"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def _ensure_browser_running(self, session_id: str) -> bool:
        """Check if browser server is alive, start if not."""
        check = await self.executor.run_command(
            session_id,
            "pgrep -f browser_server.py | head -1"
        )
        if check.get("success") and check.get("output", "").strip():
            return True
        
        # Start browser server
        logger.info("Starting browser_server.py...")
        await self.executor.run_command(
            session_id,
            "DISPLAY=:1 nohup python3 /home/ubuntu/workspace/browser_server.py "
            "> /tmp/browser_server.log 2>&1 &"
        )
        # Wait for it to initialize
        for _ in range(10):
            await asyncio.sleep(1)
            check = await self.executor.run_command(
                session_id,
                "pgrep -f browser_server.py | head -1"
            )
            if check.get("success") and check.get("output", "").strip():
                logger.info("Browser server started.")
                await asyncio.sleep(2)  # Let Chromium open
                return True
        
        logger.error("Browser server failed to start")
        return False

    async def execute(
        self,
        session_id: str,
        action: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            # Ensure browser is running
            if not await self._ensure_browser_running(session_id):
                return {
                    "success": False,
                    "error": "Browser server could not be started. "
                             "Ensure DISPLAY=:1 and Chromium are available."
                }

            payload = {"action": action, **kwargs}
            payload_json = json.dumps(payload, ensure_ascii=False)

            # Write command atomically (write to temp, then rename)
            safe_json = shlex.quote(payload_json)
            write_cmd = (
                f"printf '%s' {safe_json} > {CMD_FILE}.tmp && "
                f"mv {CMD_FILE}.tmp {CMD_FILE}"
            )
            write_result = await self.executor.run_command(session_id, write_cmd)
            if not write_result.get("success"):
                return {"success": False, "error": "Failed to write browser command"}

            # Poll for result with adaptive timeout
            timeout = 45 if action == "navigate" else 20
            start = time.time()
            
            while time.time() - start < timeout:
                check = await self.executor.run_command(
                    session_id,
                    f"test -f {RES_FILE} && echo EXISTS"
                )
                if "EXISTS" in check.get("output", ""):
                    # Read and remove atomically
                    read_result = await self.executor.run_command(
                        session_id,
                        f"cat {RES_FILE} && rm -f {RES_FILE}"
                    )
                    if read_result.get("success"):
                        output = read_result.get("output", "")
                        from backend.utils.json_repair import repair_and_parse
                        parsed, err = repair_and_parse(output)
                        if parsed:
                            return parsed
                        return {
                            "success": False,
                            "error": f"Could not parse browser response: {err}"
                        }
                await asyncio.sleep(0.3)

            return {
                "success": False,
                "error": f"Browser action '{action}' timed out after {timeout}s. "
                         f"The page may still be loading."
            }

        except Exception as e:
            logger.error(f"BrowserTool error: {e}")
            return {"success": False, "error": str(e)}
