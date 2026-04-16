import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)

class MCPTool:
    """
    Agentic tool to dynamically connect new MCP servers.
    This allows the agent to 'install' or 'connect' new capabilities on the fly.
    """
    def __init__(self, mcp_client, sync_callback: Optional[Callable] = None):
        self.mcp_client = mcp_client
        self.sync_callback = sync_callback

    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "mcp_connect",
            "description": "Interact with MCP servers. Use action='list_catalog' to see available servers, or action='connect' to connect a new one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["connect", "list_catalog"],
                        "description": "Action to perform"
                    },
                    "server_name": {
                        "type": "string",
                        "description": "Short, unique name for the server (e.g., 'google-search')"
                    },
                    "command": {
                        "type": "string",
                        "description": "The command to run (e.g., 'npx', 'python', 'node')"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments for the command"
                    }
                },
                "required": ["action"]
            }
        }

    async def execute(self, action: str = "connect", server_name: str = "", command: str = "", args: List[str] = [], **kwargs) -> Dict[str, Any]:
        """Dynamically add a new MCP server and discover its tools."""
        try:
            if action == "list_catalog":
                from backend.mcp_hub.marketplace import MCP_CATALOG
                return {
                    "success": True,
                    "catalog": list(MCP_CATALOG.keys()),
                    "message": "To connect, use action='connect' with server_name and command from catalog."
                }
            
            # For connect action, lookup in catalog if command is missing
            if action == "connect" and not command and server_name:
                from backend.mcp_hub.marketplace import MCP_CATALOG
                if server_name in MCP_CATALOG:
                    command = MCP_CATALOG[server_name]["command"]
                    args = MCP_CATALOG[server_name].get("args", [])

            # Check if already connected
            if server_name in self.mcp_client.sessions:
                return {
                    "success": False,
                    "error": f"MCP Server '{server_name}' is already connected."
                }

            # Update config (for the instance)
            self.mcp_client.servers_config[server_name] = {
                "command": command,
                "args": args
            }

            # Connect
            from mcp import StdioServerParameters
            server_params = StdioServerParameters(
                command=self.mcp_client._normalize_command(command), 
                args=args
            )
            
            # Start connection task
            asyncio.create_task(self.mcp_client._connect_server(server_name, server_params))
            
            # Wait for actual connection (up to 15 seconds)
            connected = await self.mcp_client.wait_for_connection(
                server_name, timeout=15.0
            )
            if not connected:
                return {
                    "success": False,
                    "error": (
                        f"MCP server '{server_name}' failed to connect "
                        f"within 15 seconds. Check if '{command}' is installed."
                    )
                }
            # Sync tools in the registry
            if self.sync_callback:
                await self.sync_callback()
            
            # Get newly discovered tools for the result message
            all_tools = await self.mcp_client.discover_tools()
            new_tools = [t for t in all_tools if t["function"]["_mcp_server"] == server_name]
            
            return {
                "success": True,
                "output": f"Successfully connected to MCP server '{server_name}'. Discovered {len(new_tools)} new tools.",
                "new_tools": [t["function"]["name"] for t in new_tools]
            }
        except Exception as e:
            logger.error(f"MCPTool error: {e}")
            return {"success": False, "error": str(e)}
