import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TriggerTool:
    """Установка отложенных задач или условных триггеров на основе времени."""
    
    _triggers: Dict[str, asyncio.Task] = {}

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "trigger",
                "description": "Schedule a task to run after a delay.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["add", "cancel", "list"]},
                        "delay_seconds": {"type": "integer"},
                        "task_description": {"type": "string"},
                        "trigger_id": {"type": "string"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, delay_seconds: int = 0,
                      task_description: str = None, trigger_id: str = None, 
                      session_id: str = None, **kwargs) -> Dict[str, Any]:
        
        if action == "add":
            if not task_description:
                return {"success": False, "error": "task_description required"}
            tid = f"trig_{abs(hash(task_description))}_{delay_seconds}"
            
            async def delayed_execution():
                await asyncio.sleep(delay_seconds)
                logger.info(f"Trigger {tid} fired: {task_description}")
                # TODO: Dispatch back to agent event queue
                # For an MVP, we just log it. A full impl would push to the websocket handler 
                # or agent's processing loop.
            
            self._triggers[tid] = asyncio.create_task(delayed_execution())
            return {"success": True, "output": f"Trigger {tid} set for {delay_seconds}s"}
            
        elif action == "cancel":
            if trigger_id in self._triggers:
                self._triggers[trigger_id].cancel()
                del self._triggers[trigger_id]
                return {"success": True, "output": f"Cancelled {trigger_id}"}
            return {"success": False, "error": "Not found"}
        
        elif action == "list":
            return {"success": True, "output": f"Active triggers: {list(self._triggers.keys())}"}
            
        return {"success": False, "error": "Unknown action"}
