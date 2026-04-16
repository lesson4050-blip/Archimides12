import logging
from mcp.server.fastmcp import FastMCP
from backend.agent.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class ArchimedesMCPServer:
    """
    Exposes Archimedes native tools via Model Context Protocol (MCP).
    Allows external agents to utilize Archimedes' capabilities.
    """
    def __init__(self, tool_registry: ToolRegistry):
        self.mcp = FastMCP("Archimedes Tools")
        self.tool_registry = tool_registry
        self._register_tools()

    def _register_tools(self):
        for defn in self.tool_registry.get_all_tool_definitions():
            func_name = defn["function"]["name"]
            func_desc = defn["function"]["description"]
            self._make_mcp_tool(func_name, func_desc)

    def _make_mcp_tool(self, func_name: str, func_desc: str):
        @self.mcp.tool(name=func_name, description=func_desc)
        async def mcp_wrapper(**kwargs) -> str:
            session_id = kwargs.pop("session_id", "mcp-external")
            result = await self.tool_registry.execute_tool(
                func_name, kwargs, session_id=session_id
            )
            if result.get("success"):
                return str(result.get("output", result.get("content", "OK")))
            return f"Error: {result.get('error', 'Unknown error')}"

    def run(self, host: str = "0.0.0.0", port: int = 8002):
        """Run the MCP server (typically stdio or sse)."""
        logger.info(f"Starting Archimedes MCP Server on {host}:{port}")
        # FastMCP handles the transport internals
        self.mcp.run()

if __name__ == "__main__":
    # For testing standalone
    from backend.agent.core import ArchimedesCosmoAgent
    agent = ArchimedesCosmoAgent()
    server = ArchimedesMCPServer(agent.tool_registry)
    server.run()
