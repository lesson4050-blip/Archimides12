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
                                "click_coordinates",  # Click at exact x,y pixel position
                                "type",        # Type into input field
                                "type_and_submit",  # Type + press Enter
                                "scroll",      # Scroll page
                                "screenshot",  # Take screenshot
                                "get_elements", # List all interactive elements
                                "get_dom_tree", # Full structured DOM tree (for SPA analysis)
                                "inject_js",   # Execute arbitrary JavaScript on the page
                                "wait_for",    # Wait for element to appear
                                "current_state", # Get URL/title/elements (no content)
                                "vision_analyze", # Analyze current page visually
                                "save_session",    # Save login state
                                "clear_session"    # Clear cookies
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
                        },
                        "x": {
                            "type": "number",
                            "description": "X pixel coordinate for click_coordinates action"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y pixel coordinate for click_coordinates action"
                        },
                        "script": {
                            "type": "string",
                            "description": "JavaScript code to execute for inject_js action"
                        },
                        "question": {
                            "type": "string",
                            "description": "Question for vision_analyze action"
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

    async def _analyze_with_vision(
        self,
        session_id: str,
        screenshot_path: str,
        question: str
    ) -> str:
        """
        Use multimodal model to analyze browser screenshot.
        Falls back to text-only if vision not available.
        """
        try:
            # Read screenshot from container
            read_res = await self.executor.run_command(
                session_id,
                f"base64 {screenshot_path} 2>/dev/null"
            )
            if not read_res.get("success"):
                return ""

            b64_image = read_res.get("output", "").strip()
            if not b64_image:
                return ""

            # Try Gemini vision (free tier)
            from backend.config import settings
            if settings.GOOGLE_API_KEY:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.0-flash",
                    contents=[
                        types.Content(parts=[
                            types.Part(text=question),
                            types.Part(inline_data=types.Blob(
                                mime_type="image/png",
                                data=b64_image
                            ))
                        ])
                    ]
                )
                return response.text or ""

            # Try Ollama with vision model if available
            import ollama as ollama_lib
            import base64
            img_bytes = base64.b64decode(b64_image)
            response = await asyncio.to_thread(
                ollama_lib.chat,
                model="llava:7b",  # or minicpm-v, qwen2.5-vl
                messages=[{
                    "role": "user",
                    "content": question,
                    "images": [img_bytes]
                }]
            )
            return response.message.content or ""

        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            return ""

    async def execute(
        self,
        session_id: str,
        action: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            if action == "vision_analyze":
                question = kwargs.get("question", "What do you see on this page?")
                # First get screenshot
                screenshot_result = await self.execute(
                    session_id, "screenshot",
                    filename="/tmp/browser_vision.png"
                )
                if not screenshot_result.get("success"):
                    return {"success": False, "error": "Could not take screenshot"}

                vision_text = await self._analyze_with_vision(
                    session_id,
                    "/tmp/browser_vision.png",
                    question
                )
                # Also get DOM text as backup
                current = await self.execute(session_id, "current_state")

                return {
                    "success": True,
                    "vision_analysis": vision_text,
                    "url": current.get("url", ""),
                    "elements": current.get("elements", []),
                    "hint": "Use vision_analysis to understand what to click next"
                }

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

            # Poll for result with adaptive timeout and retry on timeout
            timeout = 45 if action == "navigate" else 20
            first_attempt = True
            start = time.time()
            
            while True:
                elapsed = time.time() - start
                if elapsed >= timeout:
                    if first_attempt:
                        # Restart browser server and retry once
                        logger.warning(
                            f"Browser timeout on '{action}'. "
                            f"Restarting browser server and retrying..."
                        )
                        await self.executor.run_command(
                            session_id,
                            "pkill -f browser_server.py; sleep 1"
                        )
                        await self._ensure_browser_running(session_id)
                        first_attempt = False
                        start = time.time()
                        # Write command again
                        await self.executor.run_command(session_id, write_cmd)
                        continue  # retry the poll loop
                    else:
                        break  # Give up after retry

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
                "error": f"Browser action '{action}' timed out after retry. "
                         f"The page may still be loading."
            }

        except Exception as e:
            logger.error(f"BrowserTool error: {e}")
            return {"success": False, "error": str(e)}
