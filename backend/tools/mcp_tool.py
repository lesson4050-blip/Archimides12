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
            "description": "Connect to a new external MCP server to expand your toolset. Example: connect to 'server-fetch' via npx.",
            "parameters": {
                "type": "object",
                "properties": {
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
                        "description": "Arguments for the command (e.g., ['-y', '@modelcontextprotocol/server-google-search'])"
                    }
                },
                "required": ["server_name", "command"]
            }
        }

    async def execute(self, server_name: str, command: str, args: List[str] = [], **kwargs) -> Dict[str, Any]:
        """Dynamically add a new MCP server and discover its tools."""
        try:
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
            
            # Wait for discovery
            await asyncio.sleep(5)
            
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
