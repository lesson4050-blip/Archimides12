"""
Git Tool — standard git operations for the agent.
Distinct from git_forensics (which does archaeology/blame).
This tool handles active development: status, diff, add, commit, push.
"""
import subprocess
import asyncio
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


class GitTool:
    """Standard git operations: status, diff, add, commit, push, log."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "git",
                "description": (
                    "Execute standard git operations. Use for: checking status, "
                    "viewing diffs, staging files, committing, pushing changes. "
                    "For code archaeology (blame, log analysis), use git_forensics."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "status", "diff", "diff_staged",
                                "add", "commit", "push",
                                "log", "stash", "checkout", "branch"
                            ],
                            "description": (
                                "status: show working tree status. "
                                "diff: show unstaged changes. "
                                "diff_staged: show staged changes. "
                                "add: stage files (path or '.' for all). "
                                "commit: commit staged changes with message. "
                                "push: push to remote. "
                                "log: show recent commits. "
                                "stash: stash/pop working changes. "
                                "checkout: switch branch or restore file. "
                                "branch: list or create branches."
                            )
                        },
                        "path": {
                            "type": "string",
                            "description": "File path or '.' for all (for add/checkout)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Commit message (for commit action)"
                        },
                        "args": {
                            "type": "string",
                            "description": "Additional arguments (e.g. branch name)"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory (default: /home/ubuntu/workspace)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(
        self,
        action: str,
        path: str = ".",
        message: str = None,
        args: str = None,
        cwd: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        cwd = cwd or os.environ.get(
            "WORKSPACE_DIR", "/home/ubuntu/workspace"
        )

        command_map = {
            "status": ["git", "status", "--short"],
            "diff": ["git", "diff"],
            "diff_staged": ["git", "diff", "--staged"],
            "add": ["git", "add", path],
            "commit": (
                ["git", "commit", "-m", message]
                if message
                else ["git", "commit", "--allow-empty-message", "-m", ""]
            ),
            "push": ["git", "push"],
            "log": ["git", "log", "--oneline", "-10"],
            "stash": ["git", "stash"] + ([args] if args else []),
            "checkout": (
                ["git", "checkout", args]
                if args else ["git", "checkout", path]
            ),
            "branch": ["git", "branch"] + ([args] if args else []),
        }

        if action not in command_map:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }

        cmd = command_map[action]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=30.0
                )
            except asyncio.TimeoutError:
                proc.kill()
                return {"success": False, "error": "Git timed out"}

            output = (stdout + stderr).decode("utf-8", errors="replace")
            success = proc.returncode == 0
            return {
                "success": success,
                "output": output.strip() or "(no output)",
                "return_code": proc.returncode,
            }
        except FileNotFoundError:
            return {"success": False, "error": "git not found in PATH"}
        except Exception as e:
            logger.error(f"GitTool error: {e}")
            return {"success": False, "error": str(e)}
