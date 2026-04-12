import logging
import asyncio
import sys
from typing import Dict, List, Any, Optional
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
import anyio

logger = logging.getLogger(__name__)

class ArchimedesMCPClient:
    """
    Connects Archimedes to external MCP servers to expand its toolset.
    Supports primarily stdio transport for local binaries/npx.
    """
    def __init__(self, external_servers: Dict[str, Dict[str, Any]]):
        self.servers_config = external_servers
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack: Dict[str, anyio.abc.AsyncResource] = {}
        self.external_tools: List[Dict[str, Any]] = []
        self._stop_events: Dict[str, asyncio.Event] = {}

    async def connect_all(self):
        """Initialize connections to all configured external servers."""
        for name, config in self.servers_config.items():
            try:
                if config.get("command"):
                    # stdio transport logic
                    params = StdioServerParameters(
                        command=self._normalize_command(config["command"]),
                        args=config.get("args", []),
                        env=config.get("env")
                    )
                    asyncio.create_task(self._connect_server(name, params))
                    
                logger.info(f"MCP Client: Integrated external server '{name}'")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{name}': {e}")

    async def _connect_server(self, name: str, params: StdioServerParameters):
        """Helper to manage the lifecycle of a single server session."""
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.sessions[name] = session
                    
                    # Discover tools
                    tools_result = await session.list_tools()
                    for tool in tools_result.tools:
                        # Normalize tool definition for Archimedes
                        tool_def = {
                            "type": "function",
                            "function": {
                                "name": f"mcp_{name}_{tool.name}",
                                "description": f"[MCP: {name}] {tool.description}",
                                "parameters": tool.inputSchema,
                                "_mcp_server": name,
                                "_mcp_tool_name": tool.name
                            }
                        }
                        self.external_tools.append(tool_def)
                        logger.info(f"MCP Client: Discovered tool '{tool.name}' on server '{name}'")
                    
                    # Fix 13: Replace busy-wait with Event
                    stop_event = asyncio.Event()
                    self._stop_events[name] = stop_event
                    await stop_event.wait()
                        
        except Exception as e:
            logger.error(f"MCP Server '{name}' session error: {e}")
            self.sessions.pop(name, None)
            self._stop_events.pop(name, None)

    async def disconnect_server(self, name: str):
        """Disconnect and cleanup a single MCP server."""
        if name in self._stop_events:
            self._stop_events[name].set()
            self.sessions.pop(name, None)
            self._stop_events.pop(name, None)
            logger.info(f"MCP Client: Disconnected server '{name}'")

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Fetch all available tools from all connected servers."""
        return self.external_tools

    async def call_external_tool(self, server_name: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on an external MCP server."""
        if server_name in self.sessions:
            session = self.sessions[server_name]
            try:
                result = await session.call_tool(tool_name, arguments=params)
                # MCP results can have multiple pieces of content
                output = "\n".join([c.text for c in result.content if hasattr(c, "text")])
                return {"success": True, "output": output}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Server '{server_name}' not connected."}

    def _normalize_command(self, command: str) -> str:
        """Handle Windows-specific command resolution (e.g., npx -> npx.cmd)."""
        if sys.platform == "win32":
            if command in ["npx", "npm"]:
                return f"{command}.cmd"
        return command
