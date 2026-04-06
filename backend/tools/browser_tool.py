import logging
from typing import Dict, Any, Optional
from backend.sandbox.executor import SandboxExecutor

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

    async def execute(self, session_id: str, action: str, url: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # Browser actions are executed via a python script inside the container
        # Note: we use playwright (already installed in Dockerfile)
        
        # We generate a small python script to perform the action and output JSON
        # Example action: navigate
        if action == "navigate":
            if not url:
                return {"success": False, "error": "URL is required for 'navigate' action."}
                
            script = f"""
import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto({url!r}, wait_until="networkidle")
        title = await page.title()
        text = await page.evaluate("document.body.innerText")
        print(json.dumps({{"title": title, "text": text[:5000]}})) # Truncate for now
        await browser.close()

asyncio.run(run())
"""
            tmp_script = f"/tmp/browser_{action}.py"
            cmd = f"""cat << 'EOF' > {tmp_script}
{script.strip()}
EOF
python3 {tmp_script}"""
            return await self.executor.run_command(session_id, cmd)
            
        elif action == "screenshot":
            # Very similar logic but saving a file
            filename = kwargs.get("filename", f"screenshot_{session_id}.png")
            script = f"""
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto({url!r})
        await page.screenshot(path={f"/home/ubuntu/workspace/{filename}"!r})
        print(f"Screenshot saved to {filename}")
        await browser.close()
asyncio.run(run())
"""
            tmp_script = f"/tmp/browser_{action}.py"
            cmd = f"""cat << 'EOF' > {tmp_script}
{script.strip()}
EOF
python3 {tmp_script}"""
            return await self.executor.run_command(session_id, cmd)
            
        else:
            return {"success": False, "error": f"Action '{action}' not yet fully implemented in BrowserTool MVP."}
