import asyncio
import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

class PersistentShell:
    """Держит один bash процесс живым весь lifetime сессии."""
    
    _sentinel_counter = 0  # Class-level monotonic counter
    
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
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
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
        
        # Inject ACI tools (SWE-agent style)
        init_script = """
function search_dir() {
    grep -rnI "$1" .
}
function find_file() {
    find . -type f -name "*$1*"
}
function str_replace_editor() {
    python3 -c '
import sys
file, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(file, "r") as f: content = f.read()
    if old in content:
        with open(file, "w") as f: f.write(content.replace(old, new))
        print("Replaced successfully")
    else:
        print("Error: old string not found in file")
except Exception as e:
    print("Error:", e)
' "$1" "$2" "$3"
}
export -f search_dir find_file str_replace_editor
"""
        # We need to wait a tiny bit for the socket to be ready
        await asyncio.sleep(0.5)
        await self.run(init_script, timeout=5)

    async def run(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        async with self._lock:
            if not self._socket:
                return {"success": False, "error": "Shell not started"}
            
            PersistentShell._sentinel_counter += 1
            sentinel = f"__DONE_{PersistentShell._sentinel_counter}__"
            full_cmd = f"{command}; echo {sentinel}\n"
            loop = asyncio.get_running_loop()
            
            try:
                await loop.run_in_executor(None, 
                    lambda: self._socket._sock.send(full_cmd.encode()))
            except (OSError, BrokenPipeError, ConnectionResetError) as e:
                logger.error(f"Shell socket dead: {e}")
                self._socket = None
                return {"success": False, "error": f"Shell connection lost: {e}"}
            
            output = ""
            deadline = loop.time() + timeout
            while loop.time() < deadline:
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
                except (OSError, ConnectionResetError) as e:
                    logger.error(f"Shell socket error during recv: {e}")
                    self._socket = None
                    return {"success": False, "error": f"Shell connection lost: {e}"}
                except Exception as e:
                    logger.error(f"Exception during shell recv: {e}")
                    break
            
            logger.warning(f"Shell command timed out after {timeout} seconds.")
            return {"success": False, "error": "Timeout: command execution incomplete."}

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
