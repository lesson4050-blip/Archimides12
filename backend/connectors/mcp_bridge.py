"""
MCP Bridge: registers connected services as tools in Archimedes'
tool registry. The agent can then call them directly.

When user connects GitHub:
-> MCP bridge registers tool "github_list_repos", "github_read_file" etc.
-> Agent sees these tools and uses them to solve tasks.
"""
import inspect
import logging
from typing import Dict, Any, List
from backend.connectors.registry import CONNECTOR_CATALOG
from backend.connectors.service import nango
from backend.connectors.tools import get_tools
from backend.agent.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ConnectorMCPBridge:
    def __init__(self, tool_registry: ToolRegistry, user_id: str):
        self.registry = tool_registry
        self.user_id = user_id
        self._registered: Dict[str, List[str]] = {}

    async def sync_connected_services(self):
        """
        Called on session start and after connect/disconnect.
        Loads user's active connections and registers them as tools.
        """
        try:
            connections = await nango.list_connections(self.user_id)
        except Exception as e:
            logger.warning(f"MCP Bridge: failed to list connections: {e}")
            return

        active_integrations = {
            c["provider_config_key"] for c in connections
        }

        for integration_key in active_integrations:
            await self._register_service_tools(
                integration_key, self.user_id
            )

        logger.info(
            f"MCP Bridge: {len(active_integrations)} services active "
            f"for user {self.user_id}"
        )

    async def _register_service_tools(
        self, integration: str, connection_id: str
    ):
        """Register all tool functions for a connected service."""
        if integration in self._registered:
            return  # Already registered

        tools_instance = get_tools(integration, connection_id)
        if not tools_instance:
            logger.warning(
                f"No tool class for integration: {integration}"
            )
            return

        registered_names = []

        # Get catalog info
        catalog_entry = next(
            (v for v in CONNECTOR_CATALOG.values()
             if v["nango_key"] == integration),
            None
        )
        service_name = (
            catalog_entry["name"] if catalog_entry else integration
        )

        # Register each public method as a tool
        for attr_name in dir(tools_instance):
            if attr_name.startswith('_'):
                continue
            method = getattr(tools_instance, attr_name, None)
            if not callable(method) or not inspect.iscoroutinefunction(method):
                continue

            tool_name = f"{integration.replace('-', '_')}_{attr_name}"

            # Capture method in closure properly
            async def make_tool_func(m=method):
                async def tool_func(**kwargs) -> Dict[str, Any]:
                    try:
                        result = await m(**kwargs)
                        return {
                            "success": True,
                            "output": str(result),
                            "raw": result
                        }
                    except Exception as e:
                        return {"success": False, "error": str(e)}
                return tool_func

            func = await make_tool_func()
            definition = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": (
                        f"[{service_name}] {attr_name.replace('_', ' ').title()} "
                        f"— uses your connected {service_name} account"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "kwargs": {
                                "type": "object",
                                "description": "Parameters for this action"
                            }
                        }
                    }
                }
            }
            self.registry.register_tool(definition, func)
            registered_names.append(tool_name)

        self._registered[integration] = registered_names
        logger.info(
            f"MCP Bridge: registered {len(registered_names)} tools "
            f"for {service_name}"
        )

    def get_active_services_context(self) -> str:
        """
        Returns a string injected into agent system prompt
        telling it what services are available.
        """
        if not self._registered:
            return ""

        lines = ["CONNECTED SERVICES (you can use these tools):"]
        for integration, tools in self._registered.items():
            tool_names = [t.split('_', 2)[-1] if '_' in t else t for t in tools[:5]]
            lines.append(
                f"  * {integration}: {', '.join(tool_names)}"
                + (" ..." if len(tools) > 5 else "")
            )
        return "\n".join(lines)
