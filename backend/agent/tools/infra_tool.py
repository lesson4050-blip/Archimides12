"""
Infrastructure Management Tool (Sprint 6.1).

This tool allows Archimedes to manage its own execution environment.
Features:
- Check and fix pip dependency conflicts
- Update requirements.txt
- Auto-install missing packages based on import errors
- Inspect container/system state
"""
import os
import sys
import subprocess
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class InfraTool:
    @staticmethod
    def get_definition() -> Dict[str, Any]:
        return {
            "name": "infra",
            "description": "Manage the environment dependencies and infrastructure (Docker, Pip).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check_deps", "fix_deps", "install", "docker_status", "docker_rebuild", "system_info"],
                        "description": "Action to perform on the infrastructure."
                    },
                    "packages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of packages to install (only for 'install' action)."
                    }
                },
                "required": ["action"]
            }
        }

    @staticmethod
    async def execute(params: Dict[str, Any], workspace_dir: str = ".") -> Dict[str, Any]:
        action = params.get("action")
        
        try:
            if action == "check_deps":
                return InfraTool._check_deps()
            elif action == "fix_deps":
                return InfraTool._fix_deps(workspace_dir)
            elif action == "install":
                packages = params.get("packages", [])
                return InfraTool._install(packages)
            elif action == "docker_status":
                return InfraTool._docker_status(workspace_dir)
            elif action == "docker_rebuild":
                return InfraTool._docker_rebuild(workspace_dir)
            elif action == "system_info":
                return InfraTool._system_info()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"InfraTool error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _check_deps() -> Dict[str, Any]:
        """Run pip check to find conflicts."""
        result = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "output": "All dependencies are satisfied. No conflicts found."}
        else:
            return {
                "success": False, 
                "output": "Dependency conflicts found.",
                "details": result.stdout.strip() or result.stderr.strip()
            }

    @staticmethod
    def _fix_deps(workspace_dir: str) -> Dict[str, Any]:
        """Attempt to fix dependencies based on requirements.txt."""
        req_file = os.path.join(workspace_dir, "requirements.txt")
        if not os.path.exists(req_file):
            return {"success": False, "error": f"requirements.txt not found in {workspace_dir}"}
            
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "output": "Dependencies updated.",
            "details": result.stdout[-500:] if result.returncode == 0 else result.stderr[-500:]
        }

    @staticmethod
    def _install(packages: List[str]) -> Dict[str, Any]:
        """Install specific packages."""
        if not packages:
            return {"success": False, "error": "No packages specified."}
            
        result = subprocess.run([sys.executable, "-m", "pip", "install"] + packages, capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "output": f"Installed {', '.join(packages)}.",
            "details": result.stdout[-500:] if result.returncode == 0 else result.stderr[-500:]
        }

    @staticmethod
    def _docker_status(workspace_dir: str) -> Dict[str, Any]:
        """Check docker compose status."""
        try:
            result = subprocess.run(["docker", "compose", "ps"], cwd=workspace_dir, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return {"success": True, "output": result.stdout.strip()}
            else:
                return {"success": False, "error": "Docker is not running or docker-compose.yml not found.", "details": result.stderr.strip()}
        except FileNotFoundError:
            return {"success": False, "error": "Docker CLI not found on system."}

    @staticmethod
    def _docker_rebuild(workspace_dir: str) -> Dict[str, Any]:
        """Rebuild docker compose containers."""
        try:
            result = subprocess.run(["docker", "compose", "up", "-d", "--build"], cwd=workspace_dir, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return {"success": True, "output": "Docker containers successfully rebuilt and started.", "details": result.stdout[-500:]}
            else:
                return {"success": False, "error": "Failed to rebuild Docker containers.", "details": result.stderr[-500:]}
        except FileNotFoundError:
            return {"success": False, "error": "Docker CLI not found on system."}

    @staticmethod
    def _system_info() -> Dict[str, Any]:
        """Return basic system context."""
        import platform
        return {
            "success": True,
            "output": f"OS: {platform.system()} {platform.release()}",
            "python_version": sys.version,
            "architecture": platform.machine()
        }
