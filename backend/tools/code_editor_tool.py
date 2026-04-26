"""
Multi-file Code Editor Tool.
Enables surgical edits to existing code files:
- find_and_replace: replace exact string in file
- insert_after: insert code after a specific line/pattern
- insert_before: insert code before a specific line/pattern
- delete_block: delete lines between two patterns

This is critical for SWE-bench tasks that require precise patches
without rewriting entire files.
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CodeEditorTool:
    """Surgical multi-file code editing without full rewrites."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "code_edit",
                "description": (
                    "Surgically edit existing code files. "
                    "Use instead of file(action='write') when you need to "
                    "modify specific parts of a large file without rewriting it. "
                    "Supports: find_replace, insert_after, insert_before, delete_block, "
                    "view_lines (show specific line range)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "find_replace", "insert_after",
                                "insert_before", "delete_block",
                                "view_lines", "view_function"
                            ]
                        },
                        "path": {
                            "type": "string",
                            "description": "File path to edit"
                        },
                        "old_str": {
                            "type": "string",
                            "description": "Exact string to find (for find_replace, insert_after, insert_before, delete_block)"
                        },
                        "new_str": {
                            "type": "string",
                            "description": "Replacement string or code to insert"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Start line number (for view_lines, 1-indexed)"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "End line number (for view_lines)"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Function or class name to view (for view_function)"
                        }
                    },
                    "required": ["action", "path"]
                }
            }
        }

    async def execute(
        self,
        action: str,
        path: str,
        old_str: str = None,
        new_str: str = None,
        start_line: int = None,
        end_line: int = None,
        function_name: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"File not found: {path}"}

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.splitlines()

            if action == "view_lines":
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                selected = lines[start:end]
                output = "\n".join(
                    f"{start + i + 1:4d}  {line}"
                    for i, line in enumerate(selected)
                )
                return {"success": True, "output": output}

            elif action == "view_function":
                if not function_name:
                    return {"success": False, "error": "function_name required"}
                import ast
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            if node.name == function_name:
                                start = node.lineno - 1
                                end = node.end_lineno
                                selected = lines[start:end]
                                output = "\n".join(
                                    f"{start + i + 1:4d}  {line}"
                                    for i, line in enumerate(selected)
                                )
                                return {"success": True, "output": output,
                                        "start_line": start + 1, "end_line": end}
                    return {"success": False, "error": f"Function '{function_name}' not found"}
                except SyntaxError as e:
                    return {"success": False, "error": f"Syntax error in file: {e}"}

            elif action == "find_replace":
                if old_str is None:
                    return {"success": False, "error": "old_str required"}
                if old_str not in content:
                    # Show context to help debug
                    excerpt = content[:500]
                    return {
                        "success": False,
                        "error": f"String not found in {path}. File starts with:\n{excerpt}"
                    }
                count = content.count(old_str)
                if count > 1:
                    return {
                        "success": False,
                        "error": f"Ambiguous: found {count} occurrences of old_str. "
                                 f"Make old_str more specific."
                    }
                new_content = content.replace(old_str, new_str or "", 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return {
                    "success": True,
                    "output": f"Replaced 1 occurrence in {path}"
                }

            elif action == "insert_after":
                if old_str is None or new_str is None:
                    return {"success": False, "error": "old_str and new_str required"}
                if old_str not in content:
                    return {"success": False, "error": f"Anchor string not found in {path}"}
                new_content = content.replace(old_str, old_str + "\n" + new_str, 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return {"success": True, "output": f"Inserted code after anchor in {path}"}

            elif action == "insert_before":
                if old_str is None or new_str is None:
                    return {"success": False, "error": "old_str and new_str required"}
                if old_str not in content:
                    return {"success": False, "error": f"Anchor string not found in {path}"}
                new_content = content.replace(old_str, new_str + "\n" + old_str, 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return {"success": True, "output": f"Inserted code before anchor in {path}"}

            elif action == "delete_block":
                if old_str is None:
                    return {"success": False, "error": "old_str (block to delete) required"}
                if old_str not in content:
                    return {"success": False, "error": f"Block not found in {path}"}
                new_content = content.replace(old_str, "", 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return {"success": True, "output": f"Deleted block from {path}"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}
        except Exception as e:
            logger.error(f"CodeEditorTool error: {e}")
            return {"success": False, "error": str(e)}
