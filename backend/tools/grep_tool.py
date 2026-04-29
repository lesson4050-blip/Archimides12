"""
Grep Tool — Fast regex search across codebase.
Uses ripgrep (rg) for performance, falls back to grep.
"""
import asyncio
import logging
import shutil
from typing import Dict, Any

logger = logging.getLogger(__name__)


class GrepTool:
    """Search file contents using regex patterns."""

    def __init__(self):
        self._rg_path = shutil.which("rg")
        self._grep_path = shutil.which("grep")

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "grep",
                "description": "Search for patterns in files using regex. Fast codebase search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Regex pattern to search for"},
                        "path": {"type": "string", "description": "Directory or file to search", "default": "."},
                        "file_pattern": {"type": "string", "description": "Glob to filter files (e.g. '*.py')"},
                        "case_insensitive": {"type": "boolean", "default": False},
                        "max_results": {"type": "integer", "default": 50},
                        "context_lines": {"type": "integer", "default": 0},
                    },
                    "required": ["pattern"],
                }
            }
        }

    async def execute(self, pattern: str, path: str = ".", file_pattern: str = "",
                      case_insensitive: bool = False, max_results: int = 50,
                      context_lines: int = 0, **kwargs) -> Dict[str, Any]:
        if not pattern:
            return {"error": "Pattern is required"}
        max_results = min(max_results, 200)
        cmd = self._build_command(pattern, path, file_pattern, case_insensitive, max_results, context_lines)
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd="/app"
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode("utf-8", errors="replace")
            lines = output.strip().split("\n") if output.strip() else []
            return {"matches": lines[:max_results], "total_matches": len(lines), "truncated": len(lines) > max_results, "command": cmd}
        except asyncio.TimeoutError:
            return {"error": "Search timed out after 30s"}
        except Exception as e:
            return {"error": str(e)}

    def _build_command(self, pattern, path, file_pattern, case_insensitive, max_results, context):
        if self._rg_path:
            cmd = "rg --no-heading --line-number"
            if case_insensitive:
                cmd += " -i"
            if file_pattern:
                cmd += f" -g '{file_pattern}'"
            if context > 0:
                cmd += f" -C {context}"
            cmd += f" -m {max_results} '{pattern}' {path}"
        else:
            cmd = "grep -rn"
            if case_insensitive:
                cmd += " -i"
            if file_pattern:
                cmd += f" --include='{file_pattern}'"
            if context > 0:
                cmd += f" -C {context}"
            cmd += f" '{pattern}' {path} | head -{max_results}"
        return cmd
