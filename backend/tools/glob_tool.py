"""
Glob Tool — Fast file name/path pattern matching.
Find files by name pattern without searching contents.
"""
import glob as glob_module
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class GlobTool:
    """Find files by glob pattern."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "glob",
                "description": "Find files by name pattern (e.g. '**/*.py', 'src/**/*.ts'). Does NOT search file contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Glob pattern"},
                        "path": {"type": "string", "description": "Base directory", "default": "."},
                        "max_results": {"type": "integer", "default": 100},
                    },
                    "required": ["pattern"],
                }
            }
        }

    async def execute(self, pattern: str, path: str = ".", max_results: int = 100, **kwargs) -> Dict[str, Any]:
        if not pattern:
            return {"error": "Pattern is required"}
        max_results = min(max_results, 1000)
        try:
            full_pattern = str(Path(path) / pattern)
            matches = sorted(glob_module.glob(full_pattern, recursive=True))
            return {"files": matches[:max_results], "total_matches": len(matches), "truncated": len(matches) > max_results, "pattern": full_pattern}
        except Exception as e:
            return {"error": str(e)}
