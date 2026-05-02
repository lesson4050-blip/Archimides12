from typing import Dict, Any, Optional
from backend.agent.shared_blackboard import SharedBlackboard

class BlackboardTool:
    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "blackboard",
                "description": "Write or append data to the Shared Blackboard for cross-agent communication and state preservation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["set", "append", "delete"], "description": "The action to perform on the blackboard"},
                        "key": {"type": "string", "description": "The key to store the data under"},
                        "value": {"type": "string", "description": "The data value to store (can be a JSON string)"}
                    },
                    "required": ["action", "key"]
                }
            }
        }

    async def execute(self, action: str = "set", key: str = "", value: Any = None, **kwargs) -> Dict[str, Any]:
        """
        Write or append data to the Shared Blackboard for cross-agent communication and state preservation.
        """
        if not key:
            return {"success": False, "error": "key is required"}
        if action != "delete" and value is None:
            return {"success": False, "error": "value is required for set and append actions"}

        blackboard = SharedBlackboard()
        
        if action == "set":
            success = await blackboard.set(key, value)
            return {"success": success, "message": f"Value set for key '{key}'"}
        elif action == "append":
            success = await blackboard.append_list(key, value)
            return {"success": success, "message": f"Value appended to list at key '{key}'"}
        elif action == "delete":
            success = await blackboard.set(key, None)
            return {"success": success, "message": f"Value cleared for key '{key}'"}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


