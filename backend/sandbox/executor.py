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
        if self._socket:
            try:
                if hasattr(self._socket, '_sock'):
                    self._socket._sock.close()
                else:
                    self._socket.close()
            except (TimeoutError, OSError, ValueError) as e:
                logging.getLogger(__name__).warning(f"Sandbox execution error: {e}")
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
    if [ -z "$1" ]; then
        echo "Error: Pattern parameter is required. Usage: search_dir \\"pattern\\""
        return 1
    fi
    grep -rnI "$1" . | head -n 50
}
function find_file() {
    if [ -z "$1" ]; then
        echo "Error: Filename parameter is required. Usage: find_file \\"filename\\""
        return 1
    fi
    find . -type f -name "*$1*" | head -n 50
}
function str_replace_editor() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo "Error: File path and old_string are required. Usage: str_replace_editor \\"file_path\\" \\"old_string\\" \\"new_string\\""
        return 1
    fi
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
            
            sock = self._socket._sock if hasattr(self._socket, '_sock') else self._socket
            
            try:
                await loop.run_in_executor(None, 
                    lambda: sock.send(full_cmd.encode()))
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
                            lambda: sock.recv(4096)),
                        timeout=2.0
                    )
                    if chunk:
                        output += chunk.decode("utf-8", errors="replace")
                        if sentinel in output:
                            output = output.split(sentinel)[0].strip()
                            # remove the echoed command string if it's there
                            if full_cmd in output:
                                output = output.replace(full_cmd, "", 1).strip()
                            
                            # Smart truncation (first/last 1000 chars) with explanatory instructions
                            if len(output) > 3000:
                                truncated_marker = f"\n\n... [OUTPUT TRUNCATED - total {len(output)} characters. " \
                                                   f"Showing first 1000 and last 1000 characters to prevent token overflow. " \
                                                   f"Use 'grep' or 'tail' to read specific lines] ...\n\n"
                                output = output[:1000] + truncated_marker + output[-1000:]
                            
                            return {"success": True, "output": output}
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
    Executes shell commands inside a sandbox container or MicroVM.
    Supports timeouts and capturing output.
    """
    def __init__(self, manager: 'SandboxManager'):
        self.manager = manager
        logger.info("SandboxExecutor initialized (Docker isolation).")

    async def run_command(self, session_id: str, command: str, timeout: int = 60, user: str = "ubuntu", detach: bool = False) -> Dict[str, Any]:
        return await self._run_in_docker(session_id, command, timeout, user, detach)

    async def _run_in_docker(self, session_id: str, command: str, timeout: int = 60, user: str = "ubuntu", detach: bool = False) -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            try:
                import subprocess
                import os
                loop = asyncio.get_running_loop()
                
                base_workspace = os.path.abspath("./workspace")
                session_workspace = os.path.abspath(os.path.join(base_workspace, session_id))
                os.makedirs(session_workspace, exist_ok=True)
                
                def _run_local():
                    res = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=session_workspace
                    )
                    return res.returncode, res.stdout, res.stderr
                
                exit_code, stdout, stderr = await loop.run_in_executor(None, _run_local)
                output_str = stdout + stderr
                return {
                    "success": exit_code == 0,
                    "exit_code": exit_code,
                    "output": output_str,
                    "error": output_str if exit_code != 0 else None
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": f"Command timed out after {timeout} seconds."}
            except Exception as e:
                logger.error(f"Local command execution error: {e}")
                return {"success": False, "error": str(e)}

        # Wrap command in timeout and bash
        cmd_list = ["timeout", str(timeout), "bash", "-c", command] if not detach else ["bash", "-c", command]
        
        try:
            loop = asyncio.get_running_loop()
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
