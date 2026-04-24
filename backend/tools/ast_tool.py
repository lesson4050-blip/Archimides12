"""
AST Tool v2: Semantic code navigation AND editing.

Key upgrades over v1:
- replace_function: Replace an entire function body via AST
- replace_class: Replace an entire class via AST
- add_import: Safely add imports without duplicates
- dependency_graph: Show which functions/classes depend on what
- Full async support
"""
import ast
import os
import re
from typing import Dict, Any, List, Optional, Set


class ASTTool:
    """
    Semantic code navigation AND editing for Python files using AST.
    Provides safe, structure-aware code modifications that avoid
    the fragility of line-number-based or string-based patching.
    """

    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "ast_navigator",
                "description": (
                    "Navigate and EDIT Python codebases using Abstract Syntax Trees (AST). "
                    "Actions: find_class, find_function, get_imports, outline, "
                    "replace_function, replace_class, add_import, dependency_graph. "
                    "For replace actions, provide 'new_code' with the replacement source."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "find_class", "find_function",
                                "get_imports", "outline",
                                "replace_function", "replace_class",
                                "add_import", "dependency_graph"
                            ]
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to the Python file to analyze or modify"
                        },
                        "target": {
                            "type": "string",
                            "description": (
                                "Name of the class or function to find/replace "
                                "(optional for outline/get_imports)"
                            )
                        },
                        "new_code": {
                            "type": "string",
                            "description": (
                                "Replacement source code for replace_function/replace_class, "
                                "or import statement for add_import "
                                "(e.g., 'from typing import Optional')"
                            )
                        }
                    },
                    "required": ["action", "path"]
                }
            }
        }

    async def execute(
        self,
        session_id: str,
        action: str,
        path: str,
        target: str = None,
        new_code: str = None
    ) -> Dict[str, Any]:
        if not os.path.exists(path) or not path.endswith(".py"):
            return {"success": False, "error": f"Invalid python file path: {path}"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error in file: {e.msg} at line {e.lineno}"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to parse AST: {str(e)}"}

        # ─── Navigation actions ────────────────────────────────

        if action == "outline":
            return self._outline(tree, code)

        elif action == "find_class":
            return self._find_class(tree, target)

        elif action == "find_function":
            return self._find_function(tree, target)

        elif action == "get_imports":
            return self._get_imports(tree)

        elif action == "dependency_graph":
            return self._dependency_graph(tree, target)

        # ─── Editing actions ──────────────────────────────────

        elif action == "replace_function":
            return self._replace_function(code, tree, path, target, new_code)

        elif action == "replace_class":
            return self._replace_class(code, tree, path, target, new_code)

        elif action == "add_import":
            return self._add_import(code, tree, path, new_code)

        return {"success": False, "error": f"Unknown action: {action}"}

    # ─── Navigation ────────────────────────────────────────────

    def _outline(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """Get a structured outline of the file."""
        classes = []
        functions = []
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    {
                        "name": m.name,
                        "start_line": m.lineno,
                        "end_line": m.end_lineno,
                        "args": [a.arg for a in m.args.args if a.arg != "self"],
                        "decorators": [
                            self._decorator_name(d) for d in m.decorator_list
                        ]
                    }
                    for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes.append({
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "bases": [self._name_of(b) for b in node.bases],
                    "methods": methods,
                    "docstring": ast.get_docstring(node)
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "args": [a.arg for a in node.args.args],
                    "decorators": [
                        self._decorator_name(d) for d in node.decorator_list
                    ],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "docstring": ast.get_docstring(node)
                })

        total_lines = len(code.split("\n"))
        return {
            "success": True,
            "total_lines": total_lines,
            "classes": classes,
            "functions": functions
        }

    def _find_class(self, tree: ast.AST, target: str) -> Dict[str, Any]:
        if not target:
            return {"success": False, "error": "target name required"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == target:
                methods = [
                    m.name for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                return {
                    "success": True,
                    "found": True,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "methods": methods,
                    "bases": [self._name_of(b) for b in node.bases],
                    "docstring": ast.get_docstring(node)
                }
        return {"success": True, "found": False}

    def _find_function(self, tree: ast.AST, target: str) -> Dict[str, Any]:
        if not target:
            return {"success": False, "error": "target name required"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
                return {
                    "success": True,
                    "found": True,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "args": [a.arg for a in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [
                        self._decorator_name(d) for d in node.decorator_list
                    ],
                    "docstring": ast.get_docstring(node)
                }
        return {"success": True, "found": False}

    def _get_imports(self, tree: ast.AST) -> Dict[str, Any]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "module": f"{module}.{alias.name}",
                        "from": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
        return {"success": True, "imports": imports}

    def _dependency_graph(
        self, tree: ast.AST, target: Optional[str]
    ) -> Dict[str, Any]:
        """
        Build a dependency graph showing which names each function/class uses.
        If target is specified, show only dependencies for that symbol.
        """
        graph = {}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                used_names: Set[str] = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        used_names.add(child.id)
                    elif isinstance(child, ast.Attribute):
                        if isinstance(child.value, ast.Name):
                            used_names.add(f"{child.value.id}.{child.attr}")
                # Remove self-references and builtins
                used_names.discard(name)
                used_names.discard("self")
                graph[name] = sorted(used_names)

        if target and target in graph:
            return {
                "success": True,
                "target": target,
                "dependencies": graph[target],
                "dependents": [
                    k for k, v in graph.items() if target in v
                ]
            }

        return {"success": True, "graph": graph}

    # ─── Editing ───────────────────────────────────────────────

    def _replace_function(
        self,
        code: str,
        tree: ast.AST,
        path: str,
        target: str,
        new_code: str
    ) -> Dict[str, Any]:
        """Replace an entire function definition using AST line numbers."""
        if not target:
            return {"success": False, "error": "target function name required"}
        if not new_code:
            return {"success": False, "error": "new_code is required for replacement"}

        # Validate new code parses
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"new_code has syntax error: {e.msg} at line {e.lineno}"
            }

        # Find the function (including decorators)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
                start = node.lineno
                # Include decorators
                if node.decorator_list:
                    start = node.decorator_list[0].lineno
                end = node.end_lineno

                lines = code.split("\n")

                # Detect indentation of the original function
                original_indent = ""
                for ch in lines[start - 1]:
                    if ch in (" ", "\t"):
                        original_indent += ch
                    else:
                        break

                # Apply same indentation to new code
                new_lines = new_code.strip().split("\n")
                # Detect indentation in new_code
                new_indent = ""
                for ch in new_lines[0]:
                    if ch in (" ", "\t"):
                        new_indent += ch
                    else:
                        break
                
                # Re-indent
                reindented = []
                for line in new_lines:
                    if line.strip() == "":
                        reindented.append("")
                    elif line.startswith(new_indent):
                        reindented.append(original_indent + line[len(new_indent):])
                    else:
                        reindented.append(original_indent + line)

                # Replace lines
                lines[start - 1:end] = reindented
                new_content = "\n".join(lines)

                # Validate the result parses
                try:
                    ast.parse(new_content)
                except SyntaxError as e:
                    return {
                        "success": False,
                        "error": (
                            f"Replacement produced invalid Python: "
                            f"{e.msg} at line {e.lineno}"
                        )
                    }

                # Write back
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {
                    "success": True,
                    "replaced": target,
                    "old_lines": f"{start}-{end}",
                    "new_lines": len(reindented),
                    "total_lines": len(lines)
                }

        return {"success": False, "error": f"Function '{target}' not found in file"}

    def _replace_class(
        self,
        code: str,
        tree: ast.AST,
        path: str,
        target: str,
        new_code: str
    ) -> Dict[str, Any]:
        """Replace an entire class definition using AST line numbers."""
        if not target:
            return {"success": False, "error": "target class name required"}
        if not new_code:
            return {"success": False, "error": "new_code is required for replacement"}

        # Validate new code parses
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"new_code has syntax error: {e.msg} at line {e.lineno}"
            }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == target:
                start = node.lineno
                if node.decorator_list:
                    start = node.decorator_list[0].lineno
                end = node.end_lineno

                lines = code.split("\n")
                lines[start - 1:end] = new_code.strip().split("\n")
                new_content = "\n".join(lines)

                # Validate
                try:
                    ast.parse(new_content)
                except SyntaxError as e:
                    return {
                        "success": False,
                        "error": (
                            f"Replacement produced invalid Python: "
                            f"{e.msg} at line {e.lineno}"
                        )
                    }

                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {
                    "success": True,
                    "replaced": target,
                    "old_lines": f"{start}-{end}",
                    "new_lines": len(new_code.strip().split("\n"))
                }

        return {"success": False, "error": f"Class '{target}' not found in file"}

    def _add_import(
        self,
        code: str,
        tree: ast.AST,
        path: str,
        new_code: str
    ) -> Dict[str, Any]:
        """
        Add an import statement at the top of the file.
        Avoids duplicates — checks if the import already exists.
        """
        if not new_code:
            return {"success": False, "error": "new_code (import statement) required"}

        # Validate it's a valid import
        import_line = new_code.strip()
        try:
            parsed = ast.parse(import_line)
            if not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(parsed)):
                return {
                    "success": False,
                    "error": "new_code must be a valid import statement"
                }
        except SyntaxError:
            return {
                "success": False,
                "error": f"Invalid import syntax: {import_line}"
            }

        # Check for duplicates
        existing_imports = self._get_imports(tree)["imports"]
        for imp in existing_imports:
            if import_line in code.split("\n"):
                return {
                    "success": True,
                    "message": "Import already exists",
                    "skipped": True
                }

        # Find the last import line to insert after
        lines = code.split("\n")
        last_import_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith("import ") or
                stripped.startswith("from ") or
                stripped.startswith("#")):
                last_import_line = i

        # Insert after the last import (or after docstring/comments at top)
        insert_at = last_import_line + 1
        lines.insert(insert_at, import_line)
        new_content = "\n".join(lines)

        # Validate
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Adding import broke syntax: {e.msg}"
            }

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "success": True,
            "added": import_line,
            "at_line": insert_at + 1
        }

    # ─── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _name_of(node) -> str:
        """Extract name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{ASTTool._name_of(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "?"

    @staticmethod
    def _decorator_name(node) -> str:
        """Extract decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{ASTTool._name_of(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return ASTTool._decorator_name(node.func)
        return "?"
