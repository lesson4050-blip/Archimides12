import logging
from typing import Dict, Any, Optional
from backend.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)

class BrowserTool:
    """
    Automates Chromium inside the sandbox via Playwright.
    """
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": "Automates a web browser to navigate and interact with websites.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["navigate", "screenshot", "click", "type", "scroll"]},
                        "url": {"type": "string", "description": "URL to navigate to (for navigate/screenshot)"},
                        "selector": {"type": "string", "description": "CSS selector (for click/type)"},
                        "text": {"type": "string", "description": "Text to type (for type)"},
                        "filename": {"type": "string", "description": "Filename for screenshot"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, **kwargs) -> Dict[str, Any]:
        try:
            # Connect to the persistent browser server via JSON files
            import json
            import time
            
            cmd_file = "/tmp/browser_cmd.json"
            res_file = "/tmp/browser_res.json"
            
            payload = {"action": action, **kwargs}
            
            # Write command
            write_cmd = f"cat << 'EOF' > {cmd_file}\n{json.dumps(payload)}\nEOF"
            await self.executor.run_command(session_id, write_cmd)
            
            # Poll for result
            start_time = time.time()
            timeout = 60
            
            while time.time() - start_time < timeout:
                check_res = await self.executor.run_command(session_id, f"ls {res_file}")
                if check_res.get("success"):
                    # Read result
                    read_cmd = f"cat {res_file} && rm {res_file}"
                    res_out = await self.executor.run_command(session_id, read_cmd)
                    if res_out.get("success"):
                        from backend.utils.json_repair import repair_and_parse
                        parsed, _ = repair_and_parse(res_out.get("output", "{}"))
                        return parsed or {"success": False, "error": "Browser response parse failed"}
                await asyncio.sleep(0.5)
                
            return {"success": False, "error": "Browser action timed out or server not responding."}
        except Exception as e:
            logger.error(f"BrowserTool error: {e}")
            return {"success": False, "error": str(e)}
