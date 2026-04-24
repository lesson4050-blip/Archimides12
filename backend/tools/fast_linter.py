"""
Fast Linter Tool: Lightweight syntax + style checking for the agent.

Uses py_compile for syntax validation and a set of quick heuristic
checks for common Python antipatterns.

This is designed to be fast enough to run inside the swarm agent loop
without adding latency — no heavy external tools like pylint.
"""
import ast
import py_compile
import os
import re
import tempfile
from typing import Dict, Any, List


class FastLinterTool:
    """
    Fast, lightweight Python linter for agent self-checking.
    Runs in <100ms for typical files.
    """

    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "fast_linter",
                "description": (
                    "Fast Python code linter. Checks syntax, common bugs, "
                    "and antipatterns. Use to validate code before submitting."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["lint_file", "lint_code"]
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to Python file (for lint_file)"
                        },
                        "code": {
                            "type": "string",
                            "description": "Python code string (for lint_code)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(
        self,
        session_id: str,
        action: str,
        path: str = None,
        code: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        if action == "lint_file":
            if not path or not os.path.exists(path):
                return {"success": False, "error": f"File not found: {path}"}
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
        elif action == "lint_code":
            if not code:
                return {"success": False, "error": "code parameter required for lint_code"}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        issues = []

        # 1. Syntax check
        syntax_ok, syntax_error = self._check_syntax(code)
        if not syntax_ok:
            issues.append({
                "severity": "CRITICAL",
                "type": "syntax",
                "message": syntax_error,
                "fixable": True
            })
            # If syntax is broken, can't do further analysis
            return {
                "success": True,
                "passed": False,
                "issues": issues,
                "summary": f"CRITICAL: {syntax_error}"
            }

        # 2. AST-based checks
        try:
            tree = ast.parse(code)
            issues.extend(self._check_ast(tree, code))
        except Exception:
            pass

        # 3. Pattern-based checks
        issues.extend(self._check_patterns(code))

        passed = not any(i["severity"] == "CRITICAL" for i in issues)
        
        summary_parts = []
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = sum(1 for i in issues if i["severity"] == sev)
            if count:
                summary_parts.append(f"{count} {sev}")
        
        return {
            "success": True,
            "passed": passed,
            "issues": issues,
            "issue_count": len(issues),
            "summary": (
                "All checks passed ✅" if not issues
                else f"Found: {', '.join(summary_parts)}"
            )
        }

    def _check_syntax(self, code: str):
        """Check Python syntax using py_compile."""
        try:
            # Write to temp file for py_compile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name

            try:
                py_compile.compile(tmp_path, doraise=True)
                return True, None
            except py_compile.PyCompileError as e:
                return False, str(e)
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            return False, f"Syntax check failed: {e}"

    def _check_ast(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """AST-based checks for common issues."""
        issues = []

        for node in ast.walk(tree):
            # Bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        "severity": "HIGH",
                        "type": "bare_except",
                        "message": f"Line {node.lineno}: Bare 'except:' catches all exceptions including KeyboardInterrupt",
                        "line": node.lineno,
                        "fixable": True
                    })

            # Empty function/class body (just pass)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (len(node.body) == 1 and
                    isinstance(node.body[0], ast.Pass) and
                    not ast.get_docstring(node)):
                    issues.append({
                        "severity": "MEDIUM",
                        "type": "empty_function",
                        "message": f"Line {node.lineno}: Function '{node.name}' has empty body (just 'pass')",
                        "line": node.lineno,
                        "fixable": False
                    })

            # Mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "severity": "HIGH",
                            "type": "mutable_default",
                            "message": f"Line {node.lineno}: Function '{node.name}' uses mutable default argument",
                            "line": node.lineno,
                            "fixable": True
                        })

            # Global variable assignment
            if isinstance(node, ast.Global):
                issues.append({
                    "severity": "LOW",
                    "type": "global_var",
                    "message": f"Line {node.lineno}: 'global' statement used — consider refactoring",
                    "line": node.lineno,
                    "fixable": False
                })

            # eval/exec usage
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                    issues.append({
                        "severity": "HIGH",
                        "type": "unsafe_eval",
                        "message": f"Line {node.lineno}: '{func.id}()' used — potential security risk",
                        "line": node.lineno,
                        "fixable": True
                    })

        return issues

    def _check_patterns(self, code: str) -> List[Dict[str, Any]]:
        """Regex-based pattern checks for common issues."""
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # TODO/FIXME/HACK comments
            if re.search(r'#\s*(TODO|FIXME|HACK|XXX)', line, re.IGNORECASE):
                issues.append({
                    "severity": "LOW",
                    "type": "todo_comment",
                    "message": f"Line {i}: Unresolved TODO/FIXME comment",
                    "line": i,
                    "fixable": False
                })

            # Hardcoded credentials patterns
            if re.search(
                r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{3,}',
                line, re.IGNORECASE
            ):
                issues.append({
                    "severity": "CRITICAL",
                    "type": "hardcoded_secret",
                    "message": f"Line {i}: Possible hardcoded secret/credential",
                    "line": i,
                    "fixable": True
                })

            # Print statements in production code
            if re.match(r'\s*print\(', line) and not line.strip().startswith("#"):
                issues.append({
                    "severity": "LOW",
                    "type": "print_statement",
                    "message": f"Line {i}: print() in production code — use logging instead",
                    "line": i,
                    "fixable": True
                })

        # File-level checks
        if len(lines) > 500 and not any("class " in l for l in lines[:50]):
            issues.append({
                "severity": "MEDIUM",
                "type": "large_file",
                "message": f"File has {len(lines)} lines — consider splitting into modules",
                "fixable": False
            })

        return issues
