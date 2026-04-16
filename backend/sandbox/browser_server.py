import asyncio
import json
import os
import logging
from playwright.async_api import async_playwright

# Simple persistent browser server that lives inside the container
# It keeps a headful Chromium window open on DISPLAY :1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("browser_server")

async def main():
    logger.info("Starting persistent browser server...")
    async with async_playwright() as p:
        # Launch headful Chromium
        browser = await p.chromium.launch(
            headless=False, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--window-size=1280,720"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        # Navigate to a start page to show it's working
        await page.goto("about:blank")
        
        cmd_file = "/tmp/browser_cmd.json"
        res_file = "/tmp/browser_res.json"
        
        # Clean up old files
        if os.path.exists(cmd_file):
            os.remove(cmd_file)
        if os.path.exists(res_file):
            os.remove(res_file)
        
        logger.info("Browser window opened. Listening for commands in /tmp/browser_cmd.json")
        
        while True:
            if os.path.exists(cmd_file):
                try:
                    with open(cmd_file, "r") as f:
                        data = json.load(f)
                    os.remove(cmd_file)
                    
                    action = data.get("action")
                    logger.info(f"Executing action: {action}")
                    
                    if action == "navigate":
                        await page.goto(data.get("url"), wait_until="networkidle")
                    elif action == "click":
                        await page.click(data.get("selector"))
                    elif action == "type":
                        await page.fill(data.get("selector"), data.get("text"))
                    elif action == "scroll":
                        await page.mouse.wheel(0, 500)
                    
                    # Capture state after action
                    title = await page.title()
                    url = page.url
                    content = await page.evaluate("document.body.innerText")
                    
                    result = {
                        "success": True,
                        "title": title,
                        "url": url,
                        "content": content[:10000] # Return more content
                    }
                    
                    with open(res_file, "w") as f:
                        json.dump(result, f)
                        
                except Exception as e:
                    logger.error(f"Error executing browser action: {e}")
                    with open(res_file, "w") as f:
                        json.dump({"success": False, "error": str(e)}, f)
                        
            await asyncio.sleep(0.2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
