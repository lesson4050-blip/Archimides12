import asyncio
import httpx
import hashlib
import logging
import aiosqlite
import os
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get(
    "MONITOR_DB",
    os.path.join("data", "monitors.db")
)


async def _init_db():
    """Create a new connection with proper schema initialization."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS monitors (
                monitor_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                on_change_task TEXT,
                session_id TEXT,
                last_hash TEXT,
                last_checked TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await conn.commit()


class MonitorTool:
    """24/7 мониторинг URL с автоматическим запуском задач при изменении. Сохраняется в БД."""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._db_initialized = False
        
    async def _resurrect_monitors(self):
        try:
            async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                cursor = await conn.execute("SELECT monitor_id FROM monitors")
                rows = await cursor.fetchall()
            for row in rows:
                mid = row[0]
                if mid not in self._tasks:
                    self._tasks[mid] = asyncio.create_task(self._watch(mid))
        except Exception as e:
            logger.error(f"Failed to resurrect monitors: {e}")
    
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
        if not self._db_initialized:
            await _init_db()
            self._db_initialized = True
            await self._resurrect_monitors()

        if action == "add":
            if not url:
                return {"success": False, "error": "url required for 'add' action"}
            mid = f"mon_{abs(hash(url))}_{int(datetime.now().timestamp())}"
            
            try:
                async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                    await conn.execute(
                        "INSERT INTO monitors (monitor_id, url, interval_minutes, on_change_task, session_id) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (mid, url, interval_minutes, on_change_task, kwargs.get("session_id", ""))
                    )
                    await conn.commit()
                
                self._tasks[mid] = asyncio.create_task(self._watch(mid))
                return {"success": True, "output": f"Monitor {mid} started for {url}"}
            except Exception as e:
                return {"success": False, "error": f"DB Error: {str(e)}"}
        
        elif action == "list":
            try:
                async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                    cursor = await conn.execute(
                        "SELECT monitor_id, url, interval_minutes, last_checked "
                        "FROM monitors"
                    )
                    rows = await cursor.fetchall()
                
                if not rows:
                    return {"success": True, "output": "No active monitors."}
                
                lines = [f"{r[0]}: {r[1]} every {r[2]}min (Last check: {r[3] or 'never'})" for r in rows]
                return {"success": True, "output": "\n".join(lines)}
            except Exception as e:
                return {"success": False, "error": f"DB Error: {str(e)}"}
        
        elif action == "remove":
            if not monitor_id:
                return {"success": False, "error": "monitor_id required for 'remove'"}
            if monitor_id in self._tasks:
                self._tasks[monitor_id].cancel()
                del self._tasks[monitor_id]
                
            try:
                async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                    await conn.execute("DELETE FROM monitors WHERE monitor_id = ?", (monitor_id,))
                    await conn.commit()
                return {"success": True, "output": f"Monitor {monitor_id} removed."}
            except Exception as e:
                return {"success": False, "error": f"DB Error: {str(e)}"}
        
        elif action == "check_now":
            if not monitor_id:
                return {"success": False, "error": "monitor_id required for 'check_now'"}
            changed, content = await self._fetch_and_compare(monitor_id)
            if content.startswith("Error:"):
                 return {"success": False, "error": content}
            return {"success": True, "output": f"Changed: {changed}", "content": content[:500]}
            
        return {"success": False, "error": f"Unknown action: {action}"}

    async def _fetch_and_compare(self, mid: str) -> Tuple[bool, str]:
        try:
            async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                cursor = await conn.execute(
                    "SELECT url, last_hash FROM monitors WHERE monitor_id = ?", 
                    (mid,)
                )
                row = await cursor.fetchone()
                if not row:
                    return False, "Error: Monitor not found"
            
            url, last_hash = row
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                content = resp.text
                current_hash = hashlib.md5(content.encode()).hexdigest()
                
                changed = last_hash is not None and current_hash != last_hash
                
                await conn.execute(
                    "UPDATE monitors SET last_hash = ?, last_checked = ? WHERE monitor_id = ?",
                    (current_hash, datetime.now().isoformat(), mid)
                )
                await conn.commit()
                
                return changed, content[:2000]
        except Exception as e:
            logger.error(f"Monitor fetch error for {mid}: {e}")
            return False, f"Error: {str(e)}"

    async def _watch(self, mid: str):
        while True:
            try:
                async with aiosqlite.connect(DB_PATH, timeout=10) as conn:
                    cursor = await conn.execute(
                        "SELECT interval_minutes, on_change_task, session_id "
                        "FROM monitors WHERE monitor_id = ?", 
                        (mid,)
                    )
                    row = await cursor.fetchone()
                
                if not row:
                    break # Monitor was deleted
                    
                interval_minutes, on_change_task, session_id = row
                
                changed, _ = await self._fetch_and_compare(mid)
                if changed and on_change_task:
                    logger.info(f"Monitor {mid}: change detected — {on_change_task}")
                    try:
                        from backend.websocket.handler import manager
                        if session_id and session_id in manager.agent_loops:
                            agent = manager.agent_loops[session_id]
                            async def sender(event):
                                await manager.send_event(session_id, event)
                            asyncio.create_task(agent.process_task(
                                on_change_task,
                                websocket_send=sender
                            ))
                    except Exception as e:
                        logger.error(f"Monitor dispatch error: {e}")
                
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor watch error {mid}: {e}")
                await asyncio.sleep(60) # Backoff on error
