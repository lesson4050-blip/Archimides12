import asyncio
import httpx
import hashlib
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MonitorTool:
    """24/7 мониторинг URL с автоматическим запуском задач при изменении."""
    
    _monitors: Dict[str, Dict] = {}
    _tasks: Dict[str, asyncio.Task] = {}
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "monitor",
                "description": "Watch URLs or APIs for changes. Trigger task when change detected.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["add", "list", "remove", "check_now"]},
                        "url": {"type": "string"},
                        "interval_minutes": {"type": "integer", "default": 60},
                        "on_change_task": {"type": "string", "description": "Task for agent when change detected"},
                        "monitor_id": {"type": "string"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, url: str = None,
                      interval_minutes: int = 60, on_change_task: str = None,
                      monitor_id: str = None, **kwargs) -> Dict[str, Any]:
        if action == "add":
            if not url:
                return {"success": False, "error": "url required for 'add' action"}
            mid = f"mon_{abs(hash(url))}_{int(datetime.now().timestamp())}"
            self._monitors[mid] = {
                "url": url, "interval_minutes": interval_minutes,
                "on_change_task": on_change_task,
                "session_id": kwargs.get("session_id", ""),
                "last_hash": None, "last_checked": None
            }
            self._tasks[mid] = asyncio.create_task(self._watch(mid))
            return {"success": True, "output": f"Monitor {mid} started for {url}"}
        
        elif action == "list":
            if not self._monitors:
                return {"success": True, "output": "No active monitors."}
            lines = [f"{mid}: {m['url']} every {m['interval_minutes']}min"
                     for mid, m in self._monitors.items()]
            return {"success": True, "output": "\n".join(lines)}
        
        elif action == "remove":
            if monitor_id in self._tasks:
                self._tasks[monitor_id].cancel()
                del self._tasks[monitor_id]
            self._monitors.pop(monitor_id, None)
            return {"success": True, "output": f"Monitor {monitor_id} removed."}
        
        elif action == "check_now":
            if monitor_id not in self._monitors:
                return {"success": False, "error": "Monitor not found"}
            changed, content = await self._fetch_and_compare(monitor_id)
            return {"success": True, "output": f"Changed: {changed}", "content": content[:500]}
            
        return {"success": False, "error": f"Unknown action: {action}"}

    async def _fetch_and_compare(self, mid: str):
        m = self._monitors[mid]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(m["url"], headers={"User-Agent": "Mozilla/5.0"})
                content = resp.text
                current_hash = hashlib.md5(content.encode()).hexdigest()
                changed = m["last_hash"] is not None and current_hash != m["last_hash"]
                m["last_hash"] = current_hash
                m["last_checked"] = datetime.now().isoformat()
                return changed, content[:2000]
        except Exception as e:
            logger.error(f"Monitor fetch error for {m['url']}: {e}")
            return False, str(e)

    async def _watch(self, mid: str):
        while mid in self._monitors:
            m = self._monitors[mid]
            changed, _ = await self._fetch_and_compare(mid)
            if changed and m.get("on_change_task"):
                logger.info(f"Monitor {mid}: change detected — {m['on_change_task']}")
                try:
                    from backend.websocket.handler import manager
                    session_id = m.get("session_id", "")
                    if session_id and session_id in manager.agent_loops:
                        agent = manager.agent_loops[session_id]
                        async def sender(event):
                            await manager.send_event(session_id, event)
                        asyncio.create_task(agent.process_task(
                            m["on_change_task"],
                            websocket_send=sender
                        ))
                except Exception as e:
                    logger.error(f"Monitor dispatch error: {e}")
            await asyncio.sleep(m["interval_minutes"] * 60)
