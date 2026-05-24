"""
Shell Tool — with persistent shell sessions.

Supports both sandbox-delegated execution and local persistent
bash sessions that maintain state (cd, env vars) between calls.
"""
import asyncio
import os
import re
import sys
import shutil
from pathlib import Path
import logging
from typing import Dict, Any, Optional



from backend.sandbox.executor import SandboxExecutor
from backend.agent.predictive_guard import PredictiveGuard
from backend.tools.bash_security import validate_command as security_validate_command, SecurityResult

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
        self._is_cmd = False

    async def _ensure_started(self):
        if self._process is None or self._process.returncode is not None:
            import sys, shutil
            from pathlib import Path
            
            shell_exec = "/bin/bash"
            self._is_cmd = False
            
            if sys.platform == "win32":
                # Try Git Bash first
                git_bash_paths = [
                    r"C:\Program Files\Git\bin\bash.exe",
                    r"C:\Program Files (x86)\Git\bin\bash.exe",
                ]
                found = None
                for p in git_bash_paths:
                    if Path(p).exists():
                        found = p
                        break
                
                if found:
                    shell_exec = found
                else:
                    # Fall back to cmd.exe
                    shell_exec = "cmd.exe"
                    self._is_cmd = True
            
            self._process = await asyncio.create_subprocess_exec(
                shell_exec,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy()
            )

    async def run(self, command: str, timeout: int = 30) -> str:
        async with self._lock:
            await self._ensure_started()
            sentinel = f"__END_{id(command)}__"
            if getattr(self, '_is_cmd', False):
                full_cmd = f"{command}\r\necho {sentinel}\r\n"
            else:
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
import time
_persistent_sessions: Dict[str, PersistentShellSession] = {}
_session_last_used: Dict[str, float] = {}
_SESSION_TTL = 3600  # 1 hour

def get_persistent_session(session_id: str) -> PersistentShellSession:
    """Get or create a persistent shell session for the given session ID."""
    # Cleanup stale sessions first
    _cleanup_stale_sessions()
    
    if session_id not in _persistent_sessions:
        _persistent_sessions[session_id] = PersistentShellSession(session_id)
    _session_last_used[session_id] = time.time()
    return _persistent_sessions[session_id]

def _cleanup_stale_sessions():
    """Remove sessions inactive for more than TTL seconds."""
    now = time.time()
    stale = [
        sid for sid, last in list(_session_last_used.items())
        if now - last > _SESSION_TTL
    ]
    for sid in stale:
        session = _persistent_sessions.pop(sid, None)
        _session_last_used.pop(sid, None)
        if session:
            # Schedule async close without blocking
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(session.close())
            except Exception:
                pass


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
                    "required": ["command"]
                }
            }
        }

    async def execute(self, session_id: str = None, action: str = "exec",
                      command: Optional[str] = None, timeout: int = 60,
                      **kwargs) -> Dict[str, Any]:
        from backend.agent.self_improvement import check_tool_safety
        
        # Layer 0: PredictiveGuard (Self-Healing)
        if command:
            guard_result = await PredictiveGuard.analyze_command(command)
            if not guard_result["safe"]:
                logger.warning(f"PredictiveGuard intercepted command: {command[:50]} — {guard_result['reason']}")
                return {
                    "success": False,
                    "output": f"Command blocked by PredictiveGuard: {guard_result['reason']}\nSuggestion: {guard_result['suggestion']}",
                    "blocked": True,
                    "suggestion": guard_result["suggestion"]
                }
                
        # Layer 1: Bash security engine (fast, regex-based)
        if command:
            sec_result = security_validate_command(command)
            if not sec_result.allowed:
                logger.warning(f"BLOCKED by bash_security: {command[:50]} — {sec_result.message}")
                if getattr(sec_result, 'severity', None) == "permission_required":
                    return {
                        "success": False,
                        "output": (
                            f"⚠️ PERMISSION REQUIRED: {sec_result.message}\n"
                            f"Command: {command}\n"
                            f"To execute, user must explicitly approve this command."
                        ),
                        "permission_required": True,
                        "blocked_command": command,
                    }
                return {
                    "success": False,
                    "output": f"🛡️ BLOCKED by security engine: {sec_result.message}",
                    "exit_code": -1,
                    "blocked": True,
                    "check_id": getattr(sec_result.check_id, 'name', None) if getattr(sec_result, 'check_id', None) else None
                }
        
        # Layer 2: AI-based safety check
        if command:
            is_safe, reason = await check_tool_safety("shell", {"command": command})
            if not is_safe:
                logger.warning(f"BLOCKED command: {command[:50]} — {reason}")
                return {
                    "success": False,
                    "output": f"Command blocked: {reason}",
                    "blocked": True
                }

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
                if result.get("success"):
                    if is_background:
                        await asyncio.sleep(2)
                    await self._auto_expose_ports(session_id)
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
                    res = {"success": True, "output": f"{prefix}{output}"}
                    if is_background:
                        await asyncio.sleep(2)
                    await self._auto_expose_ports(session_id)
                    return res
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
            if result.get("success"):
                if is_background:
                    await asyncio.sleep(2)
                await self._auto_expose_ports(session_id)
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

    async def _auto_expose_ports(self, session_id: str):
        """Scans active listening ports inside the container and auto-exposes them."""
        import os
        if not session_id or os.environ.get("TESTING") == "1":
            return
        
        try:
            # Check open TCP ports in container using `ss` or `netstat`
            check_res = await self.executor.run_command(session_id, "ss -tln 2>/dev/null || netstat -tln 2>/dev/null")
            if not check_res.get("success"):
                return
            
            output = check_res.get("output", "")
            import re
            found_ports = set()
            for line in output.split("\n"):
                if "LISTEN" in line or "listen" in line.lower():
                    matches = re.findall(r'(?::|:)(\d+)\s', line)
                    for m in matches:
                        port = int(m)
                        if port not in (22, 5900, 6080, 9222):
                            found_ports.add(port)
            
            if not found_ports:
                return
            
            from backend.tools.expose_tool import ExposeTool
            expose_tool = ExposeTool(self.executor)
            event_bus = getattr(self.executor, "event_bus", None)
            
            if not hasattr(self, "_auto_exposed_ports"):
                self._auto_exposed_ports = set()
                
            for port in found_ports:
                if port not in self._auto_exposed_ports:
                    logger.info(f"Auto-Exposing detected port {port} for session {session_id}...")
                    
                    expose_res = await expose_tool.execute(session_id=session_id, port=port)
                    if expose_res.get("success"):
                        url = expose_res.get("url")
                        self._auto_exposed_ports.add(port)
                        
                        logger.info(f"Auto-Expose SUCCESS: Port {port} -> {url}")
                        
                        if event_bus:
                            from backend.agent.orchestration.event_bus import StreamEvent, EventType
                            await event_bus.emit(StreamEvent(
                                type=EventType.BROWSER_NAVIGATE,
                                content={
                                    "url": url,
                                    "title": f"Port {port} Preview"
                                },
                                agent="shell_tool",
                                session_id=session_id
                            ))
                            await event_bus.emit_thought(
                                f"🌐 Запустилось веб-приложение на порту {port}! Я автоматически проксировал его. Вкладка браузера должна открыться автоматически на адресе: {url}",
                                agent="shell_tool"
                            )
        except Exception as e:
            logger.warning(f"Failed to auto-expose ports: {e}")


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
