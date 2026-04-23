import subprocess
import os
from typing import Dict, Any

class GitForensicsTool:
    """
    Advanced Git integration for uncovering the historical context of code.
    """
    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "git_forensics",
                "description": "SUPER WEAPON: Uncover why code was written a certain way by interrogating Git history. Use this to understand the origin of a bug or find the commit that introduced a specific variable.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["blame", "search", "show"]},
                        "path": {"type": "string", "description": "Target file path (for blame)"},
                        "query": {"type": "string", "description": "Search string (for search) or Commit Hash (for show)"},
                        "lines": {"type": "string", "description": "Line range for blame e.g. '10,20'"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, path: str = None, query: str = None, lines: str = None) -> Dict[str, Any]:
        cwd = os.path.dirname(path) if path else os.getcwd()
        if path and not os.path.exists(path):
            return {"success": False, "error": f"Path not found: {path}"}

        try:
            if action == "blame":
                if not path:
                    return {"success": False, "error": "Path required for blame"}
                cmd = ["git", "blame"]
                if lines:
                    cmd.extend(["-L", lines])
                cmd.append(path)
                
            elif action == "search":
                if not query:
                    return {"success": False, "error": "Query required for search"}
                # Search for addition/deletion of string in history
                cmd = ["git", "log", "-S", query, "--oneline", "-n", "10"]
                
            elif action == "show":
                if not query:
                    return {"success": False, "error": "Commit hash required for show (passed in query)"}
                cmd = ["git", "show", query, "--stat", "-p", "--max-count=1"]
                
            else:
                return {"success": False, "error": f"Unknown action {action}"}

            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                return {"success": False, "error": result.stderr.strip() or "Git command failed"}
                
            return {"success": True, "result": result.stdout.strip()}

        except Exception as e:
            return {"success": False, "error": f"Git execution error: {str(e)}"}
