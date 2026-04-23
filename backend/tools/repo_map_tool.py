import os
import ast
from typing import Dict, Any, List

class RepoMapTool:
    """
    Generates a skeleton map of the repository, extracting class and function signatures
    for Python files to give the agent a bird's-eye view of the architecture.
    """
    def __init__(self):
        self.ignore_dirs = {'.git', '__pycache__', 'venv', 'env', 'node_modules', '.venv', '.pytest_cache', '.mypy_cache'}
        self.ignore_exts = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.class', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "repo_map",
                "description": "SUPER WEAPON: Generate a compressed 'skeleton' map of the codebase. It shows directory structure and extracts class/function signatures from Python files. Use this FIRST when exploring a new repository to understand the architecture without exceeding context limits.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Root directory path to map (use '.' for current workspace)"},
                        "max_depth": {"type": "integer", "description": "Maximum directory depth to traverse (default 3)"}
                    },
                    "required": ["path"]
                }
            }
        }

    async def execute(self, session_id: str, path: str, max_depth: int = 3) -> Dict[str, Any]:
        target_path = path
        if path == "." or path == "./":
            target_path = os.getcwd()
            
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            return {"success": False, "error": f"Invalid directory path: {target_path}"}

        tree_str = self._build_map(target_path, max_depth, current_depth=0)
        
        # If the map is extremely huge, we might truncate it, but let's try returning it all first.
        # Usually it's very compact.
        return {
            "success": True,
            "result": f"Repository Map for {target_path}:\n{tree_str}"
        }

    def _build_map(self, root_path: str, max_depth: int, current_depth: int) -> str:
        if current_depth > max_depth:
            return "    " * current_depth + "[Max depth reached...]\n"
            
        result = ""
        try:
            items = sorted(os.listdir(root_path))
        except PermissionError:
            return "    " * current_depth + "[Permission Denied]\n"

        dirs = [i for i in items if os.path.isdir(os.path.join(root_path, i)) and i not in self.ignore_dirs]
        files = [i for i in items if os.path.isfile(os.path.join(root_path, i)) and not any(i.endswith(ext) for ext in self.ignore_exts)]

        indent = "    " * current_depth
        
        for d in dirs:
            result += f"{indent}📁 {d}/\n"
            result += self._build_map(os.path.join(root_path, d), max_depth, current_depth + 1)
            
        for f in files:
            file_path = os.path.join(root_path, f)
            result += f"{indent}📄 {f}\n"
            if f.endswith('.py'):
                signatures = self._extract_python_signatures(file_path)
                if signatures:
                    for sig in signatures:
                        result += f"{indent}    └─ {sig}\n"
                        
        return result

    def _extract_python_signatures(self, filepath: str) -> List[str]:
        signatures = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    signatures.append(f"class {node.name}")
                    # Get top-level methods inside class
                    for subnode in node.body:
                        if isinstance(subnode, ast.FunctionDef):
                            signatures.append(f"  def {subnode.name}(...)")
                elif isinstance(node, ast.FunctionDef):
                    signatures.append(f"def {node.name}(...)")
        except Exception:
            # Silently ignore parsing errors for map generation
            pass
        return signatures
