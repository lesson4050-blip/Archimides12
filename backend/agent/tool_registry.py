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
        Simplified registration for tool objects or methods. 
        Creates a basic definition if none exists.
        """
        # Try to get definition from tool if it has a way to provide it
        definition = None
        
        # Check if tool_instance is a bound method (e.g., self.search_tool.execute)
        actual_instance = tool_instance
        if hasattr(tool_instance, "__self__"):
            actual_instance = tool_instance.__self__
            
        if hasattr(actual_instance, "get_definition"):
            definition = actual_instance.get_definition()
        elif hasattr(actual_instance, "definition"):
            definition = actual_instance.definition
        
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
        callback = actual_instance.execute if hasattr(actual_instance, "execute") else tool_instance
        
        self.tools[name] = callback
        self.tool_definitions.append(definition)
        logger.info(f"Registered simplified tool: {name}")

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        return self.tool_definitions

    async def execute_tool(
        self,
        name: str,
        params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        from backend.utils.tool_schemas import (
            validate_tool_call, fuzzy_match_tool_name
        )
        from backend.utils.structured_logger import log_tool_call

        # Fuzzy match tool name
        available = list(self.tools.keys())
        if name not in self.tools:
            matched = fuzzy_match_tool_name(name, available)
            if matched:
                logger.info(
                    f"Fuzzy matched tool '{name}' -> '{matched}'"
                )
                name = matched
            else:
                err = {
                    "success": False,
                    "error": (
                        f"Tool '{name}' not found. "
                        f"Available: {available}"
                    )
                }
                log_tool_call(session_id or "?", name, params, err)
                return err

        # Validate params
        validated = validate_tool_call({"name": name, "params": params})
        if validated:
            params = validated.params

        # Type coercion: fix common model mistakes
        tool_def = next(
            (d for d in self.tool_definitions
             if d.get("function", {}).get("name") == name),
            None
        )
        if tool_def:
            props = (tool_def.get("function", {})
                     .get("parameters", {})
                     .get("properties", {}))
            for key, schema in props.items():
                if key in params:
                    val = params[key]
                    expected_type = schema.get("type")
                    try:
                        if expected_type == "integer" and not isinstance(val, int):
                            params[key] = int(val)
                        elif expected_type == "boolean" and not isinstance(val, bool):
                            params[key] = str(val).lower() in ("true", "1", "yes")
                        elif expected_type == "string" and not isinstance(val, str):
                            params[key] = str(val)
                        elif expected_type == "array" and isinstance(val, str):
                            # Model passed a string instead of array
                            if val.startswith('['):
                                from backend.utils.json_repair import repair_and_parse
                                parsed, _ = repair_and_parse(val)
                                if isinstance(parsed, list):
                                    params[key] = parsed
                            else:
                                # Split by comma as fallback
                                params[key] = [v.strip() for v in val.split(',')]
                        elif expected_type == "number" and isinstance(val, str):
                            try:
                                params[key] = float(val)
                            except ValueError:
                                pass
                    except (ValueError, TypeError):
                        pass  # Keep original if conversion fails

        try:
            TOOLS_NEEDING_SESSION = {
                "file", "shell", "browser", "voice", "document",
                "slides", "expose", "plan", "monitor", "trigger",
            }
            if session_id and name in TOOLS_NEEDING_SESSION:
                params["session_id"] = session_id

            result = await self.tools[name](**params)

            if not isinstance(result, dict):
                result = {"success": True, "output": str(result)}

            log_tool_call(session_id or "?", name, params, result)
            return result

        except TypeError as e:
            # Wrong params — try calling with only session_id
            logger.warning(
                f"Tool '{name}' TypeError: {e}. "
                f"Trying with minimal params."
            )
            try:
                minimal_params = {}
                if session_id:
                    minimal_params["session_id"] = session_id
                result = await self.tools[name](**minimal_params)
                log_tool_call(session_id or "?", name, params, result)
                return result
            except Exception as e2:
                err = {"success": False, "error": str(e2)}
                log_tool_call(session_id or "?", name, params, err)
                return err

        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            err = {"success": False, "error": str(e)}
            log_tool_call(session_id or "?", name, params, err)
            return err

    def register_mcp_tool(self, definition: Dict[str, Any], callback: Callable):
        """Register a tool that comes from an external MCP server."""
        name = definition["function"]["name"]
        self.tools[name] = callback
        self.tool_definitions.append(definition)
        logger.info(f"Registered MCP tool: {name}")
