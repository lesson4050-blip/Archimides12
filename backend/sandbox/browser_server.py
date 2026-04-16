"""
Archimedes Persistent Browser Server v2
Manus-level: smart extraction, element awareness, token-efficient output.
Runs inside the sandbox container on DISPLAY :1.
"""
import asyncio
import json
import os
import re
import logging
from playwright.async_api import async_playwright, Page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("browser_server")

CMD_FILE = "/tmp/browser_cmd.json"
RES_FILE = "/tmp/browser_res.json"
MAX_TEXT_TOKENS = 3000  # ~12000 chars — enough for any LLM context


def _clean_text(raw: str) -> str:
    """Remove boilerplate noise from page text."""
    lines = raw.split("\n")
    cleaned = []
    seen = set()
    for line in lines:
        line = line.strip()
        # Skip empty, navigation noise, and duplicates
        if not line or len(line) < 3:
            continue
        if line in seen:
            continue
        # Skip common nav patterns
        if re.match(r'^(menu|nav|footer|header|cookie|subscribe|sign in|log in|×)$',
                    line, re.IGNORECASE):
            continue
        seen.add(line)
        cleaned.append(line)
    return "\n".join(cleaned)


def _truncate_smart(text: str, max_chars: int = MAX_TEXT_TOKENS * 4) -> str:
    """Truncate to max_chars, keeping beginning and key sections."""
    if len(text) <= max_chars:
        return text
    # Keep first 70% and last 30% to capture intro + conclusion
    keep_start = int(max_chars * 0.7)
    keep_end = int(max_chars * 0.3)
    return (
        text[:keep_start]
        + f"\n\n[...{len(text) - keep_start - keep_end} chars omitted...]\n\n"
        + text[-keep_end:]
    )


async def _get_interactive_elements(page: Page) -> list:
    """
    Extract clickable/interactive elements with their visible text.
    Returns lightweight list for agent decision-making.
    Max 30 elements to avoid token overload.
    """
    try:
        elements = await page.evaluate("""() => {
            const els = [];
            const selectors = [
                'a[href]', 'button', 'input[type="submit"]',
                'input[type="button"]', '[role="button"]',
                'input[type="text"]', 'input[type="search"]',
                'textarea', 'select', '[onclick]'
            ];
            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    const text = (
                        el.innerText || el.value || el.placeholder ||
                        el.getAttribute('aria-label') || el.getAttribute('title') || ''
                    ).trim().slice(0, 60);
                    if (!text) continue;
                    els.push({
                        tag: el.tagName.toLowerCase(),
                        text: text,
                        href: el.href || null,
                        type: el.type || null,
                        selector: el.id ? '#' + el.id :
                                  el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase()
                    });
                    if (els.length >= 30) break;
                }
                if (els.length >= 30) break;
            }
            return els;
        }""")
        return elements or []
    except Exception:
        return []


async def _get_main_content(page: Page) -> str:
    """
    Extract main content using readability-like heuristics.
    Falls back to body text if no main content detected.
    """
    try:
        # Try semantic HTML first
        content = await page.evaluate("""() => {
            const candidates = [
                document.querySelector('main'),
                document.querySelector('article'),
                document.querySelector('[role="main"]'),
                document.querySelector('#content'),
                document.querySelector('.content'),
                document.querySelector('#main'),
            ];
            for (const c of candidates) {
                if (c && c.innerText && c.innerText.length > 200) {
                    return c.innerText;
                }
            }
            return document.body.innerText;
        }""")
        return content or ""
    except Exception:
        try:
            return await page.inner_text("body")
        except Exception:
            return ""


async def execute_action(page: Page, data: dict) -> dict:
    action = data.get("action", "")
    
    try:
        if action == "navigate":
            url = data.get("url", "")
            if not url:
                return {"success": False, "error": "URL required"}
            
            # Navigate with smart wait
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Wait for dynamic content
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # Timeout is OK, page might still have content
            
            title = await page.title()
            content = await _get_main_content(page)
            cleaned = _clean_text(content)
            truncated = _truncate_smart(cleaned)
            elements = await _get_interactive_elements(page)
            
            # Capture screenshot for vision analysis
            screenshot_path = "/tmp/browser_current.png"
            try:
                await page.screenshot(path=screenshot_path, full_page=False)
            except Exception:
                screenshot_path = None
            
            return {
                "success": True,
                "url": page.url,
                "title": title,
                "content": truncated,
                "content_length": len(cleaned),
                "elements": elements,
                "screenshot_path": screenshot_path,
                "hint": "Use 'click' with element text or 'extract' for specific data."
            }

        elif action == "extract":
            # Smart extraction: find specific info on current page
            query = data.get("query", "")
            content = await _get_main_content(page)
            cleaned = _clean_text(content)
            
            if query:
                # Find paragraphs containing query terms
                query_lower = query.lower()
                lines = cleaned.split("\n")
                relevant = []
                for i, line in enumerate(lines):
                    if any(term in line.lower() for term in query_lower.split()):
                        # Include context: line before and after
                        start = max(0, i - 1)
                        end = min(len(lines), i + 3)
                        relevant.extend(lines[start:end])
                        relevant.append("---")
                
                if relevant:
                    return {
                        "success": True,
                        "url": page.url,
                        "extracted": "\n".join(relevant[:100]),
                        "query": query
                    }
            
            return {
                "success": True,
                "url": page.url,
                "content": _truncate_smart(cleaned, 8000)
            }

        elif action == "click":
            target = data.get("text") or data.get("selector", "")
            if not target:
                return {"success": False, "error": "text or selector required"}
            
            clicked = False
            
            # Try clicking by visible text first (most reliable for agents)
            if data.get("text"):
                try:
                    await page.click(f"text={target}", timeout=5000)
                    clicked = True
                except Exception:
                    pass
            
            # Try CSS selector
            if not clicked and data.get("selector"):
                try:
                    await page.click(target, timeout=5000)
                    clicked = True
                except Exception:
                    pass
            
            # Try partial text match
            if not clicked:
                try:
                    await page.click(f"text=/{re.escape(target)}/i", timeout=3000)
                    clicked = True
                except Exception:
                    pass
            
            if not clicked:
                return {"success": False, "error": f"Could not find clickable element: '{target}'"}
            
            await asyncio.sleep(1)
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            
            title = await page.title()
            content = await _get_main_content(page)
            cleaned = _clean_text(content)
            
            # Capture screenshot for vision analysis
            screenshot_path = "/tmp/browser_current.png"
            try:
                await page.screenshot(path=screenshot_path, full_page=False)
            except Exception:
                screenshot_path = None
            
            return {
                "success": True,
                "url": page.url,
                "title": title,
                "content": _truncate_smart(cleaned),
                "screenshot_path": screenshot_path,
                "message": f"Clicked '{target}'"
            }

        elif action == "type":
            selector = data.get("selector", "")
            text = data.get("text", "")
            if not selector or not text:
                return {"success": False, "error": "selector and text required"}
            
            # Try to find by placeholder or label first
            try:
                await page.fill(selector, text, timeout=5000)
            except Exception:
                try:
                    await page.fill(f"[placeholder*='{selector}']", text, timeout=3000)
                except Exception:
                    return {"success": False, "error": f"Could not type into: '{selector}'"}
            
            return {"success": True, "message": f"Typed '{text[:50]}...' into '{selector}'"}

        elif action == "type_and_submit":
            selector = data.get("selector", "")
            text = data.get("text", "")
            if not selector or not text:
                return {"success": False, "error": "selector and text required"}
            
            try:
                await page.fill(selector, text, timeout=5000)
                await page.press(selector, "Enter")
                await asyncio.sleep(2)
                await page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception as e:
                return {"success": False, "error": str(e)}
            
            content = await _get_main_content(page)
            return {
                "success": True,
                "url": page.url,
                "title": await page.title(),
                "content": _truncate_smart(_clean_text(content))
            }

        elif action == "scroll":
            direction = data.get("direction", "down")
            amount = data.get("amount", 500)
            dy = amount if direction == "down" else -amount
            await page.mouse.wheel(0, dy)
            await asyncio.sleep(0.5)
            content = await _get_main_content(page)
            return {
                "success": True,
                "content": _truncate_smart(_clean_text(content)),
                "message": f"Scrolled {direction} {amount}px"
            }

        elif action == "screenshot":
            path = data.get("filename", "/home/ubuntu/workspace/screenshot.png")
            await page.screenshot(path=path, full_page=False)
            return {"success": True, "path": path, "message": "Screenshot saved"}

        elif action == "get_elements":
            elements = await _get_interactive_elements(page)
            return {
                "success": True,
                "elements": elements,
                "count": len(elements),
                "hint": "Use 'click' with element 'text' field to interact"
            }

        elif action == "wait_for":
            selector = data.get("selector", "")
            timeout = data.get("timeout_ms", 5000)
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                return {"success": True, "message": f"Element '{selector}' appeared"}
            except Exception:
                return {"success": False, "error": f"Timeout waiting for '{selector}'"}

        elif action == "current_state":
            # Lightweight state check — no content, just metadata
            elements = await _get_interactive_elements(page)
            return {
                "success": True,
                "url": page.url,
                "title": await page.title(),
                "elements": elements[:10],
                "hint": "Call 'extract' to get page content"
            }

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Action '{action}' error: {e}")
        return {"success": False, "error": str(e)}


async def main():
    logger.info("Browser Server v2 starting...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1280,900",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
        )
        page = await context.new_page()
        await page.goto("about:blank")
        
        # Cleanup old files
        for f in [CMD_FILE, RES_FILE]:
            if os.path.exists(f):
                os.remove(f)
        
        logger.info(f"Ready. Listening on {CMD_FILE}")
        
        while True:
            if os.path.exists(CMD_FILE):
                result = {"success": False, "error": "Unknown"}
                try:
                    with open(CMD_FILE, "r") as f:
                        data = json.load(f)
                    os.remove(CMD_FILE)
                    logger.info(f"Executing: {data.get('action')} "
                                f"url={data.get('url','')} "
                                f"text={data.get('text','')}")
                    result = await execute_action(page, data)
                except json.JSONDecodeError as e:
                    result = {"success": False, "error": f"Bad JSON command: {e}"}
                except Exception as e:
                    result = {"success": False, "error": str(e)}
                    logger.exception("Unexpected error")
                finally:
                    try:
                        with open(RES_FILE, "w") as f:
                            json.dump(result, f, ensure_ascii=False)
                    except Exception as e:
                        logger.error(f"Failed to write result: {e}")
            
            await asyncio.sleep(0.15)  # Faster polling


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
