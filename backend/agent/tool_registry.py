from typing import Dict, Any, List, Optional, Callable
import logging
import os
import asyncio
import importlib
import inspect

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: List[Dict[str, Any]] = []
        self._ready_event = asyncio.Event()

    async def wait_until_ready(self, timeout: float = 30.0):
        """Wait for the registry to be fully initialized."""
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"ToolRegistry initialization timed out after {timeout}s")

    def set_ready(self):
        """Signal that all tools are registered."""
        self._ready_event.set()
        logger.info("ToolRegistry is now READY")

    def auto_discover_tools(
        self,
        tools_dir: str = "backend/tools",
        exclude: Optional[List[str]] = None
    ) -> int:
        """
        Sprint 4.2: Dynamic Tool Registry.
        
        Scans all Python files in the tools directory for classes that have
        both `get_definition()` and `execute()` methods. Auto-registers
        any that aren't already registered.
        
        Args:
            tools_dir: Path to scan for tool modules
            exclude: List of module names to skip (e.g., ['__init__', 'base_tool'])
            
        Returns:
            Number of newly discovered and registered tools
        """
        exclude = exclude or ["__init__", "base_tool"]
        discovered = 0
        
        if not os.path.isdir(tools_dir):
            logger.warning(f"Tools directory not found: {tools_dir}")
            return 0
        
        for filename in os.listdir(tools_dir):
            if not filename.endswith(".py"):
                continue
            
            module_name = filename[:-3]  # strip .py
            if module_name in exclude:
                continue
            
            # Convert path to importable module string
            module_path = tools_dir.replace("/", ".").replace("\\", ".") + f".{module_name}"
            
            try:
                module = importlib.import_module(module_path)
            except Exception as e:
                logger.debug(f"Skipping {module_path}: {e}")
                continue
            
            # Scan for tool classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if not inspect.isclass(attr):
                    continue
                if attr.__module__ != module.__name__:
                    continue  # Skip imported classes
                    
                has_def = hasattr(attr, "get_definition") and callable(getattr(attr, "get_definition"))
                has_exec = hasattr(attr, "execute") and callable(getattr(attr, "execute"))
                
                if not (has_def and has_exec):
                    continue
                
                # Try to get the tool name from its definition
                try:
                    instance = attr.__new__(attr)
                    # Some tools need constructor args — skip those gracefully
                    try:
                        instance.__init__()
                    except TypeError:
                        continue
                    
                    definition = instance.get_definition()
                    tool_name = definition.get("function", {}).get("name", "")
                    
                    if not tool_name:
                        continue
                    
                    # Skip if already registered
                    if tool_name in self.tools:
                        continue
                    
                    self.register(tool_name, instance.execute)
                    discovered += 1
                    logger.info(
                        f"Auto-discovered tool: {tool_name} "
                        f"from {module_path}.{attr_name}"
                    )
                    
                except Exception as e:
                    logger.debug(
                        f"Could not auto-register {attr_name} "
                        f"from {module_path}: {e}"
                    )
        
        if discovered:
            logger.info(f"Dynamic Tool Registry: {discovered} new tools discovered")
        return discovered

    def register_tool(self, definition: Dict[str, Any], func: Callable):
        name = definition["function"]["name"]
        self.tools[name] = func
        self._upsert_definition(definition)
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
        self._upsert_definition(definition)
        logger.info(f"Registered simplified tool: {name}")

    def _upsert_definition(self, definition: Dict[str, Any]):
        """Insert or replace a tool definition by name (prevents duplicates)."""
        name = definition.get("function", {}).get("name", "")
        if not name:
            self.tool_definitions.append(definition)
            return
        # Remove any existing definition with the same name
        self.tool_definitions = [
            d for d in self.tool_definitions
            if d.get("function", {}).get("name") != name
        ]
        self.tool_definitions.append(definition)

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
                "fast_linter", "ast_navigator",
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
        self._upsert_definition(definition)
        logger.info(f"Registered MCP tool: {name}")
