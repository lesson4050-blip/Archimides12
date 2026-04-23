import ast
import os
from typing import Dict, Any, List

class ASTTool:
    """
    Semantic code navigation for Python files using Abstract Syntax Trees.
    Allows the agent to find where classes/functions are defined and referenced.
    """
    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "ast_navigator",
                "description": "Navigate Python codebases using Abstract Syntax Trees (AST). Use this to semantically search for classes, functions, or variable definitions without breaking context limits.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["find_class", "find_function", "get_imports", "outline"]},
                        "path": {"type": "string", "description": "Path to the python file to analyze"},
                        "target": {"type": "string", "description": "Name of the class or function to find (optional for outline)"}
                    },
                    "required": ["action", "path"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, path: str, target: str = None) -> Dict[str, Any]:
        if not os.path.exists(path) or not path.endswith(".py"):
            return {"success": False, "error": f"Invalid python file path: {path}"}
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code)
        except Exception as e:
            return {"success": False, "error": f"Failed to parse AST: {str(e)}"}
            
        if action == "outline":
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            return {"success": True, "classes": classes, "functions": functions}
            
        elif action == "find_class":
            if not target:
                return {"success": False, "error": "target name required"}
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == target:
                    # Return the line numbers so the agent can use file_tool to view it
                    return {
                        "success": True, 
                        "found": True, 
                        "start_line": node.lineno, 
                        "end_line": node.end_lineno,
                        "docstring": ast.get_docstring(node)
                    }
            return {"success": True, "found": False}
            
        elif action == "find_function":
            if not target:
                return {"success": False, "error": "target name required"}
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == target:
                    return {
                        "success": True, 
                        "found": True, 
                        "start_line": node.lineno, 
                        "end_line": node.end_lineno,
                        "docstring": ast.get_docstring(node)
                    }
            return {"success": True, "found": False}
            
        elif action == "get_imports":
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            return {"success": True, "imports": imports}
            
        return {"success": False, "error": f"Unknown action: {action}"}
