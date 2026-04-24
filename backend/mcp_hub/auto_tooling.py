"""
Auto-Tooling: агент сам находит и подключает нужные MCP серверы.
Когда инструмента нет, ищет его в каталоге, npm, или GitHub.
"""
from backend.utils.task import safe_create_task
import asyncio
import logging
from typing import Optional, List, Dict
from backend.mcp_hub.marketplace import MCP_CATALOG

logger = logging.getLogger(__name__)


async def find_and_connect_tool(
    task_description: str,
    available_tools: List[str],
    mcp_client,
    executor,  # SandboxExecutor
    session_id: str,
    router
) -> Optional[str]:
    """
    Given a task, check if we're missing a tool and auto-connect it.
    Returns name of newly connected tool, or None.
    """
    if not mcp_client:
        logger.warning("Auto-tooling skipped: mcp_client is None")
        return None

    # Step 1: Ask LLM what tool is needed
    tool_search_prompt = f"""
A user wants to: "{task_description}"
Available tools: {available_tools}

Is there a missing tool that would help? 
Check this catalog: {list(MCP_CATALOG.keys())}

If yes, output JSON: {{"tool_name": "name_from_catalog", "reason": "why"}}
If no tool needed, output: {{"tool_name": null}}
"""
    try:
        response = await router.generate(
            messages=[{"role": "user", "content": tool_search_prompt}],
            task_hint="think"
        )
        from backend.utils.json_repair import repair_and_parse
        data, _ = repair_and_parse(response.get("text", ""))
        if not isinstance(data, dict):
            return None

        tool_name = data.get("tool_name")
        if not tool_name:
            return None

        # Step 2: Connect the tool from catalog
        catalog_entry = MCP_CATALOG.get(tool_name)
        if not catalog_entry:
            logger.info(f"Auto-tooling: '{tool_name}' not in catalog")
            return None

        # Check if npm package is available
        npm_check = await executor.run_command(
            session_id,
            f"npx --yes {catalog_entry['args'][1]} --version 2>/dev/null || echo MISSING"
        )
        if "MISSING" in npm_check.get("output", ""):
            # Install it
            pkg = catalog_entry['args'][1]
            logger.info(f"Auto-tooling: installing {pkg}...")
            await executor.run_command(
                session_id,
                f"npm install -g {pkg} 2>/dev/null",
                timeout=60
            )

        # Connect via MCP client
        from mcp import StdioServerParameters
        params = StdioServerParameters(
            command=mcp_client._normalize_command(catalog_entry["command"]),
            args=catalog_entry.get("args", [])
        )
        safe_create_task(
            mcp_client._connect_server(tool_name, params)
        )
        connected = await mcp_client.wait_for_connection(tool_name, timeout=15)

        if connected:
            logger.info(f"Auto-tooling: connected '{tool_name}'")
            return tool_name

    except Exception as e:
        logger.error(f"Auto-tooling failed: {e}")
    return None