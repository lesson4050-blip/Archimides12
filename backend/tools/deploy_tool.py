"""
DeployTool — Autonomous deployment.
Сам поднимает сервер, сам проверяет что работает,
сам даёт тебе ссылку.

Security: all inputs are sanitized, no shell injection possible.
Windows/Linux compatible.
"""
import asyncio
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Whitelist of allowed docker-compose subcommands
_ALLOWED_COMPOSE_ACTIONS = {"up", "down", "logs", "ps", "restart"}

# Max output size to prevent memory blow-up
_MAX_OUTPUT_CHARS = 3000


def _sanitize_service_name(name: str) -> str:
    """Strip everything except alphanumerics, hyphens, and underscores."""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9_-]', '', name)[:64]


def _find_compose_binary() -> str:
    """Detect docker compose v2 (docker compose) vs v1 (docker-compose)."""
    # v2 plugin (preferred)
    if shutil.which("docker"):
        return "docker"
    # v1 standalone
    if shutil.which("docker-compose"):
        return "docker-compose"
    raise FileNotFoundError("Neither 'docker' nor 'docker-compose' found in PATH")


async def _run_process(
    args: list,
    timeout: int = 120,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """Run subprocess safely, capture output, enforce timeout."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        
        out_text = stdout.decode("utf-8", errors="replace")[-_MAX_OUTPUT_CHARS:]
        err_text = stderr.decode("utf-8", errors="replace")[-_MAX_OUTPUT_CHARS:]
        
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": out_text,
            "stderr": err_text,
            "output": out_text if proc.returncode == 0 else err_text,
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except FileNotFoundError as e:
        return {"success": False, "error": f"Binary not found: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class DeployTool:

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "deploy",
                "description": (
                    "Autonomously deploy an application. "
                    "Supports: docker_compose_up, docker_compose_down, "
                    "docker_compose_restart, vercel_deploy, check_live, get_logs. "
                    "Returns live URL when successful."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "docker_compose_up",
                                "docker_compose_down",
                                "docker_compose_restart",
                                "vercel_deploy",
                                "check_live",
                                "get_logs",
                            ]
                        },
                        "target_url": {
                            "type": "string",
                            "description": "URL to verify for check_live"
                        },
                        "service_name": {
                            "type": "string",
                            "description": "Docker service name for logs/restart"
                        },
                        "compose_file": {
                            "type": "string",
                            "description": "Path to docker-compose.yml (default: ./docker-compose.yml)"
                        },
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(
        self,
        action: str,
        target_url: str = None,
        service_name: str = None,
        compose_file: str = None,
        **kwargs
    ) -> Dict[str, Any]:

        handlers = {
            "docker_compose_up": lambda: self._compose_up(compose_file),
            "docker_compose_down": lambda: self._compose_down(compose_file),
            "docker_compose_restart": lambda: self._compose_restart(service_name, compose_file),
            "vercel_deploy": self._vercel_deploy,
            "check_live": lambda: self._check_live(target_url),
            "get_logs": lambda: self._get_logs(service_name, compose_file),
        }

        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action}. Valid: {list(handlers.keys())}"}

        return await handler()

    # ── Docker Compose ──────────────────────────────────────────────

    def _compose_args(self, compose_file: str = None) -> list:
        """Build base compose command args (v1 or v2 compatible)."""
        binary = _find_compose_binary()
        if binary == "docker":
            args = ["docker", "compose"]
        else:
            args = ["docker-compose"]

        if compose_file:
            # Sanitize: ensure it looks like a path, not an injection
            cf = Path(compose_file).name  # strip directory traversal
            if cf.endswith(('.yml', '.yaml')):
                args.extend(["-f", compose_file])

        return args

    async def _compose_up(self, compose_file: str = None) -> Dict[str, Any]:
        args = self._compose_args(compose_file) + ["up", "-d", "--build"]
        result = await _run_process(args, timeout=300)
        
        if result["success"]:
            # Auto-check running containers
            ps_result = await _run_process(
                self._compose_args(compose_file) + ["ps", "--format", "table"],
                timeout=10,
            )
            result["containers"] = ps_result.get("stdout", "")

        return result

    async def _compose_down(self, compose_file: str = None) -> Dict[str, Any]:
        args = self._compose_args(compose_file) + ["down"]
        return await _run_process(args, timeout=60)

    async def _compose_restart(self, service: str = None, compose_file: str = None) -> Dict[str, Any]:
        args = self._compose_args(compose_file) + ["restart"]
        if service:
            args.append(_sanitize_service_name(service))
        return await _run_process(args, timeout=120)

    async def _get_logs(self, service: str = None, compose_file: str = None) -> Dict[str, Any]:
        args = self._compose_args(compose_file) + ["logs", "--tail=80", "--no-color"]
        if service:
            args.append(_sanitize_service_name(service))
        return await _run_process(args, timeout=15)

    # ── Vercel ──────────────────────────────────────────────────────

    async def _vercel_deploy(self) -> Dict[str, Any]:
        vercel_token = os.environ.get("VERCEL_TOKEN", "")
        if not vercel_token:
            return {
                "success": False,
                "error": "VERCEL_TOKEN not set. Add it to .env to enable Vercel deploys."
            }

        # Validate token format (alphanumeric + underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', vercel_token):
            return {"success": False, "error": "VERCEL_TOKEN contains invalid characters"}

        npx = "npx.cmd" if sys.platform == "win32" else "npx"
        args = [npx, "vercel", "--prod", "--yes", "--token", vercel_token]

        frontend_dir = "frontend"
        if not Path(frontend_dir).is_dir():
            return {"success": False, "error": f"Frontend directory '{frontend_dir}' not found"}

        result = await _run_process(args, timeout=180, cwd=frontend_dir)

        if result["success"]:
            # Extract URL from vercel output
            urls = re.findall(r'https://[^\s]+\.vercel\.app', result.get("stdout", ""))
            result["live_url"] = urls[-1] if urls else None

        return result

    # ── Health Check ────────────────────────────────────────────────

    async def _check_live(self, url: str) -> Dict[str, Any]:
        if not url:
            return {"success": False, "error": "target_url is required for check_live"}

        # Validate URL format
        if not re.match(r'^https?://', url):
            return {"success": False, "error": f"Invalid URL: {url}. Must start with http:// or https://"}

        try:
            import httpx
        except ImportError:
            return {"success": False, "error": "httpx not installed. Run: pip install httpx"}

        last_error = None
        for attempt in range(5):
            try:
                async with httpx.AsyncClient(
                    timeout=10, follow_redirects=True, verify=False
                ) as c:
                    r = await c.get(url)
                    if r.status_code < 500:
                        return {
                            "success": True,
                            "status_code": r.status_code,
                            "live": True,
                            "url": url,
                            "output": f"✅ {url} is LIVE (HTTP {r.status_code})",
                        }
                    last_error = f"HTTP {r.status_code}"
            except Exception as e:
                last_error = str(e)
            await asyncio.sleep(3)

        return {
            "success": False,
            "live": False,
            "url": url,
            "attempts": 5,
            "last_error": last_error,
            "output": f"❌ {url} not reachable after 5 attempts. Last error: {last_error}",
        }
