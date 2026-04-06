import asyncio
import logging
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

class SandboxExecutor:
    """
    Executes shell commands inside a sandbox container.
    Supports timeouts and capturing output.
    """
    def __init__(self, manager: 'SandboxManager'):
        self.manager = manager

    async def run_command(self, session_id: str, command: str, timeout: int = 60, user: str = "ubuntu") -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}

        # Wrap command in timeout and bash
        # Note: we use a list for cmd to avoid quoting issues with bash -c
        cmd_list = ["timeout", str(timeout), "bash", "-c", command]
        
        try:
            # Run using docker-py exec_run
            # execute in a separate thread to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            
            # Using partial or lambda for exec_run
            exec_res = await loop.run_in_executor(
                None, 
                lambda: container.exec_run(
                    cmd=cmd_list,
                    user=user,
                    workdir="/home/ubuntu/workspace"
                )
            )
            
            exit_code, output = exec_res
            output_str = output.decode("utf-8", errors="replace")
            
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output_str,
                "error": output_str if exit_code != 0 else None
            }
            
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Command timed out after {timeout} seconds."}
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {"success": False, "error": str(e)}
