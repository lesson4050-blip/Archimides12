from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: List[Dict[str, Any]] = []

    def register_tool(self, definition: Dict[str, Any], func: Callable):
        name = definition["function"]["name"]
        self.tools[name] = func
        self.tool_definitions.append(definition)
        logger.info(f"Registered tool: {name}")

    def register(self, name: str, tool_instance: Any):
        """
        Simplified registration for tool objects. 
        Creates a basic definition if none exists.
        """
        # Try to get definition from tool if it has a way to provide it
        definition = None
        if hasattr(tool_instance, "get_definition"):
            definition = tool_instance.get_definition()
        elif hasattr(tool_instance, "definition"):
            definition = tool_instance.definition
        
        if definition:
            # Ensure it has the OpenAI/Groq/Gemini standard 'type' field
            if "type" not in definition:
                # If the definition IS the function part, wrap it
                if "name" in definition and "parameters" in definition:
                    definition = {"type": "function", "function": definition}
                elif "function" in definition:
                    definition["type"] = "function"
                else:
                    # Generic wrap
                    definition = {"type": "function", "function": definition}
        else:
            # Fallback for MVP: simple definition
            definition = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"Executes {name} related actions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "The action to perform"},
                            "path": {"type": "string", "description": "Path if applicable"},
                            "command": {"type": "string", "description": "Command if applicable"},
                            "content": {"type": "string", "description": "Content if applicable"}
                        }
                    }
                }
            }
        
        # Use 'execute' method as the callback if it exists
        callback = tool_instance.execute if hasattr(tool_instance, "execute") else tool_instance
        
        self.tools[name] = callback
        self.tool_definitions.append(definition)
        logger.info(f"Registered simplified tool: {name}")

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        return self.tool_definitions

    async def execute_tool(self, name: str, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        if name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{name}' not found."
            }
        
        try:
            # If tool expects session_id, inject it
            if session_id:
                params["session_id"] = session_id
                
            # We assume all tool functions are async
            result = await self.tools[name](**params)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return {
                "success": False,
                "error": str(e)
            }
