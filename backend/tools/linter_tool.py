import subprocess
import os
import ast
from typing import Dict, Any

class LinterTool:
    """
    Provides instant syntax and static analysis feedback on specific files.
    """
    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "fast_linter",
                "description": "SUPER WEAPON: Instantly check a Python file for syntax errors, undefined variables, and indentation issues WITHOUT running the full test suite. Call this immediately after editing a file to ensure you didn't introduce typos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the python file to lint"}
                    },
                    "required": ["path"]
                }
            }
        }

    async def execute(self, session_id: str, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
            
        if not path.endswith('.py'):
            return {"success": False, "error": "Linter currently only supports .py files."}

        # 1. Native AST Syntax Check (catches IndentationError, SyntaxError)
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "result": f"CRITICAL SYNTAX ERROR:\nFile: {path}\nLine: {e.lineno}\nOffset: {e.offset}\nError: {e.msg}\nText: {e.text}"
            }
        except Exception as e:
            return {"success": False, "error": f"AST Parse error: {str(e)}"}

        # 2. Flake8 Static Analysis (catches Undefined variables, etc.)
        # We only care about critical errors: F821 (undefined name), E9 (syntax), F831 (duplicate arg)
        try:
            result = subprocess.run(
                ["flake8", "--select=F821,F822,F823,F831,E9", path],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0 and result.stdout.strip():
                return {
                    "success": False, 
                    "result": f"LINTER FOUND ERRORS:\n{result.stdout.strip()}\n\nPlease fix these undefined variables or syntax issues immediately."
                }
            
            return {
                "success": True,
                "result": f"File {path} passed syntax and critical linter checks. No undefined variables found."
            }
            
        except FileNotFoundError:
            return {
                "success": True,
                "result": "AST Syntax check passed (flake8 not installed, skipped deep linting)."
            }
