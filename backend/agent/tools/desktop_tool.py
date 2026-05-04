import logging
import asyncio
import os
import base64
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DesktopTool:
    """
    Anthropic-compatible Computer Use API tool.
    Allows the agent to control the desktop mouse and keyboard natively.
    Includes robust fallbacks and sandbox awareness.
    """
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "computer",
            "description": "Control the local desktop GUI (mouse, keyboard, screen). Compatible with Anthropic's Computer Use API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "key", "type", "mouse_move", "left_click", 
                            "left_click_drag", "right_click", "middle_click", 
                            "double_click", "screenshot", "cursor_position",
                            "get_accessibility_tree"
                        ]
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type or keys to press (e.g. 'ctrl+c', 'Return'). Required for 'type' and 'key' actions."
                    },
                    "coordinate": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[x, y] coordinates for mouse movement. Required for 'mouse_move' and 'left_click_drag'."
                    }
                },
                "required": ["action"]
            }
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        try:
            import pyautogui
            import pyscreenshot as ImageGrab
        except ImportError:
            return {
                "success": False, 
                "error": "pyautogui or pyscreenshot not installed. Agent must run 'pip install pyautogui pyscreenshot' to use the Desktop tool."
            }

        # Safety measure: PyAutoGUI failsafe (moving mouse to a corner throws an exception)
        pyautogui.FAILSAFE = True

        try:
            if action == "screenshot":
                # Take screenshot and return base64
                img = ImageGrab.grab()
                import io
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=80)
                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                return {
                    "success": True,
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64
                    }
                }
                
            elif action == "mouse_move":
                coords = kwargs.get("coordinate")
                if not coords or len(coords) != 2:
                    return {"success": False, "error": "coordinate [x, y] required for mouse_move"}
                pyautogui.moveTo(coords[0], coords[1], duration=0.2)
                return {"success": True, "output": f"Mouse moved to {coords}"}
                
            elif action == "left_click":
                pyautogui.click()
                return {"success": True, "output": "Left click executed"}
                
            elif action == "right_click":
                pyautogui.rightClick()
                return {"success": True, "output": "Right click executed"}
                
            elif action == "double_click":
                pyautogui.doubleClick()
                return {"success": True, "output": "Double click executed"}
                
            elif action == "left_click_drag":
                coords = kwargs.get("coordinate")
                if not coords or len(coords) != 2:
                    return {"success": False, "error": "coordinate [x, y] required for left_click_drag"}
                pyautogui.dragTo(coords[0], coords[1], duration=0.5, button='left')
                return {"success": True, "output": f"Dragged to {coords}"}
                
            elif action == "type":
                text = kwargs.get("text")
                if text is None:
                    return {"success": False, "error": "text required for 'type' action"}
                pyautogui.write(text, interval=0.01)
                return {"success": True, "output": f"Typed {len(text)} characters"}
                
            elif action == "key":
                text = kwargs.get("text")
                if text is None:
                    return {"success": False, "error": "text required for 'key' action"}
                # Handle 'ctrl+c' style chords
                keys = text.lower().split('+')
                if len(keys) > 1:
                    pyautogui.hotkey(*keys)
                else:
                    pyautogui.press(text)
                return {"success": True, "output": f"Key pressed: {text}"}
                
            elif action == "cursor_position":
                x, y = pyautogui.position()
                return {"success": True, "output": f"[{x}, {y}]"}
                
            elif action == "get_accessibility_tree":
                # Manus-level OS accessibility parsing (Linux X11 fallback)
                try:
                    # Attempt to dump window tree using xwininfo asynchronously
                    process = await asyncio.create_subprocess_exec(
                        "xwininfo", "-root", "-tree",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    try:
                        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        return {"success": False, "error": "xwininfo command timed out after 5 seconds"}
                        
                    if process.returncode == 0:
                        return {"success": True, "output": stdout.decode('utf-8')[:2000] + "\n...[truncated]"}
                    return {"success": False, "error": stderr.decode('utf-8')}
                except Exception as e:
                    return {"success": False, "error": f"Accessibility parsing failed: {e}"}
                
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except pyautogui.FailSafeException:
            return {"success": False, "error": "FAILSAFE triggered. Mouse moved to screen corner. Action aborted."}
        except Exception as e:
            logger.error(f"DesktopTool execution failed: {e}")
            return {"success": False, "error": str(e)}
