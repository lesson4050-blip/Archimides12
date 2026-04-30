"""
Tool Definition Cache — replaces O(n) dir() reflection.

Caches LLM-facing tool definitions after first build.
Invalidated automatically when register_tool() is called.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ToolDefinitionCache:
    """
    Caches tool definitions for LLM consumption.
    Replaces the expensive dir()-based reflection in the old _get_tool_definitions().
    """

    def __init__(self, agent_instance):
        self._agent = agent_instance
        self._cache: List[Dict[str, Any]] = []
        self._dirty = True

    def invalidate(self):
        """Mark cache as dirty — next get_definitions() will rebuild."""
        self._dirty = True

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Return cached tool definitions, rebuilding if invalidated."""
        if not self._dirty and self._cache:
            return self._cache

        definitions = []
        try:
            for attr_name in dir(self._agent):
                obj = getattr(self._agent, attr_name, None)
                if obj and hasattr(obj, 'get_definition') and callable(obj.get_definition):
                    try:
                        defn = obj.get_definition()
                        if "function" in defn:
                            definitions.append(defn)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Blind exception caught: {e}")

            # Manual message tool definition
            definitions.append({
                "type": "function",
                "function": {
                    "name": "message",
                    "description": "Send a final result to the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["result"]},
                            "content": {"type": "string"}
                        },
                        "required": ["type", "content"]
                    }
                }
            })
        except Exception as e:
            logger.warning(f"Failed to build tool definitions: {e}")

        self._cache = definitions
        self._dirty = False
        logger.info(
            f"ToolDefinitionCache: built {len(definitions)} definitions: "
            f"{[d.get('function', {}).get('name', '?') for d in definitions]}"
        )
        return self._cache
