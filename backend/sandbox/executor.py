import asyncio
import logging
import os
import select
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

class PersistentShell:
    """Держит один bash процесс живым весь lifetime сессии."""
    
    def __init__(self, container):
        self.container = container
        self._exec_id = None
        self._socket = None
        self._lock = asyncio.Lock()

    def stop(self):
        """Close the socket and discard the shell session securely."""
        if self._socket and hasattr(self._socket, '_sock'):
            try:
                self._socket._sock.close()
            except Exception:
                pass
        self._socket = None

    async def start(self):
        loop = asyncio.get_running_loop()
        self._exec_id = await loop.run_in_executor(None, lambda: 
            self.container.client.api.exec_create(
                self.container.id,
                cmd=["/bin/bash"],
                stdin=True, stdout=True, stderr=True, tty=True,
                workdir="/home/ubuntu/workspace",
                user="ubuntu",
                environment={"DISPLAY": ":1", "LANG": "en_US.UTF-8"}
            )
        )
        self._socket = await loop.run_in_executor(None, lambda:
            self.container.client.api.exec_start(
                self._exec_id["Id"], detach=False, tty=True, socket=True
            )
        )

    async def run(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        async with self._lock:
            if not self._socket:
                return {"success": False, "error": "Shell not started"}
            
            sentinel = f"__DONE_{id(command)}__"
            full_cmd = f"{command}; echo {sentinel}\n"
            loop = asyncio.get_running_loop()
            
            await loop.run_in_executor(None, 
                lambda: self._socket._sock.send(full_cmd.encode()))
            
            output = ""
            deadline = asyncio.get_running_loop().time() + timeout
            while asyncio.get_running_loop().time() < deadline:
                try:
                    chunk = await asyncio.wait_for(
                        loop.run_in_executor(None, 
                            lambda: self._socket._sock.recv(4096)),
                        timeout=2.0
                    )
                    if chunk:
                        output += chunk.decode("utf-8", errors="replace")
                        if sentinel in output:
                            output = output.split(sentinel)[0].strip()
                            # remove the echoed command string if it's there
                            if full_cmd in output:
                                output = output.replace(full_cmd, "", 1).strip()
                            
                            return {"success": True, "output": output[:3000]}
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Exception during shell recv: {e}")
                    break
            
            logger.warning(f"Shell command timed out after {timeout} seconds.")
            return {"success": False, "error": f"Timeout: command execution incomplete."}

class SandboxExecutor:
    """
    Executes shell commands inside a sandbox container.
    Supports timeouts and capturing output.
    """
    def __init__(self, manager: 'SandboxManager'):
        self.manager = manager

    async def run_command(self, session_id: str, command: str, timeout: int = 60, user: str = "ubuntu", detach: bool = False) -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}

        # Wrap command in timeout and bash
        # Note: we use a list for cmd to avoid quoting issues with bash -c
        cmd_list = ["timeout", str(timeout), "bash", "-c", command] if not detach else ["bash", "-c", command]
        
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
                    workdir="/home/ubuntu/workspace",
                    environment={
                        "DISPLAY": ":1",
                        "LANG": "en_US.UTF-8",
                        "LC_ALL": "en_US.UTF-8"
                    },
                    detach=detach
                )
            )
            
            if detach:
                return {"success": True, "output": "Command started in detached mode."}
            
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
