"""
Shell Tool — with persistent shell sessions.

Supports both sandbox-delegated execution and local persistent
bash sessions that maintain state (cd, env vars) between calls.
"""
import asyncio
import os
import re
import logging
from typing import Dict, Any, Optional

from backend.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)


# ── FIX 4: Persistent Shell Session ──

class PersistentShellSession:
    """
    Maintains a long-lived bash process that preserves state between commands.
    Working directory, environment variables, and shell state persist across calls.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()

    async def _ensure_started(self):
        if self._process is None or self._process.returncode is not None:
            self._process = await asyncio.create_subprocess_exec(
                "/bin/bash",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy()
            )

    async def run(self, command: str, timeout: int = 30) -> str:
        async with self._lock:
            await self._ensure_started()
            sentinel = f"__END_{id(command)}__"
            full_cmd = f"{command}\necho '{sentinel}'\n"
            self._process.stdin.write(full_cmd.encode())
            await self._process.stdin.drain()
            output_lines = []
            try:
                async with asyncio.timeout(timeout):
                    while True:
                        line = await self._process.stdout.readline()
                        decoded = line.decode(errors="replace").rstrip()
                        if sentinel in decoded:
                            break
                        output_lines.append(decoded)
            except (asyncio.TimeoutError, TimeoutError):
                output_lines.append(f"[TIMEOUT after {timeout}s]")
            return "\n".join(output_lines)

    async def close(self):
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()


# Module-level session registry
_persistent_sessions: Dict[str, PersistentShellSession] = {}


def get_persistent_session(session_id: str) -> PersistentShellSession:
    """Get or create a persistent shell session for the given session ID."""
    if session_id not in _persistent_sessions:
        _persistent_sessions[session_id] = PersistentShellSession(session_id)
    return _persistent_sessions[session_id]


async def close_session(session_id: str):
    """Close and remove a persistent session."""
    session = _persistent_sessions.pop(session_id, None)
    if session:
        await session.close()


# ── Shell Tool ──

class ShellTool:
    """
    Executes shell commands in the sandbox.
    Falls back to PersistentShellSession when sandbox shell is unavailable.
    """

    def __init__(self, executor: SandboxExecutor):
        self.executor = executor

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "shell",
                "description": "Executes a bash command in the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["exec"]},
                        "command": {"type": "string", "description": "The command to execute"}
                    },
                    "required": ["action", "command"]
                }
            }
        }

    async def execute(self, session_id: str = None, action: str = "exec",
                      command: Optional[str] = None, timeout: int = 60,
                      **kwargs) -> Dict[str, Any]:
        if action == "run":
            action = "exec"

        if action == "exec":
            if not command:
                return {"success": False, "error": "Command is required"}

            is_background = (
                command.strip().endswith(' &') or
                command.strip().startswith('nohup ')
            )

            # Try sandbox shell first
            result = await self._run_via_sandbox(session_id, command, timeout, is_background)
            if result is not None:
                return result

            # Fallback: persistent local session (if session_id provided)
            if session_id:
                try:
                    session = get_persistent_session(session_id)
                    effective_timeout = 10 if is_background else timeout
                    output = await session.run(command, timeout=effective_timeout)
                    if isinstance(output, str) and len(output) > 2000:
                        output = output[:2000] + "\n...[truncated]"
                    prefix = "Background process started. " if is_background else ""
                    return {"success": True, "output": f"{prefix}{output}"}
                except Exception as e:
                    logger.warning(f"Persistent session failed: {e}, falling back to executor")

            # Final fallback: one-shot execution via executor
            result = await self.executor.run_command(
                session_id or "default", command,
                timeout=10 if is_background else timeout
            )
            output = result.get("output", "")
            if isinstance(output, str) and len(output) > 2000:
                result["output"] = output[:2000] + "\n...[truncated]"
            return result

        elif action == "view":
            return {"success": True, "output": "Terminal view is streaming in real-time to the 'Actions' tab."}

        elif action == "wait":
            seconds = kwargs.get("seconds", 1)
            await asyncio.sleep(seconds)
            return {"success": True, "output": f"Waited {seconds} seconds."}

        elif action == "kill":
            pid = kwargs.get("pid")
            if not pid:
                return {"success": False, "error": "PID is required for 'kill' action."}
            if not re.match(r'^\d+$', str(pid)):
                return {"success": False, "error": "Invalid PID. Must be a number."}
            return await self.executor.run_command(session_id or "default", f"kill -9 {int(pid)}")

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def _run_via_sandbox(self, session_id: str, command: str,
                               timeout: int, is_background: bool) -> Optional[Dict[str, Any]]:
        """Try to run via sandbox shell. Returns None if unavailable."""
        try:
            from backend.sandbox.singleton import sandbox_manager
            shell = sandbox_manager._shells.get(session_id)
            if shell:
                try:
                    effective_timeout = 10 if is_background else timeout
                    result = await shell.run(command.strip(), timeout=effective_timeout)
                except AttributeError as e:
                    if '_sock' in str(e):
                        result = await self.executor.run_command(
                            session_id, command.strip(),
                            timeout=10 if is_background else timeout
                        )
                    else:
                        raise

                output = result.get("output", "")
                if is_background:
                    return {"success": True, "output": f"Background process started. {output.strip()}"}
                if isinstance(output, str) and len(output) > 2000:
                    result["output"] = output[:2000] + "\n...[truncated]"
                return result
        except ImportError:
            pass
        return None
