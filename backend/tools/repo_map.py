"""
AST-based Repository Map — Aider-inspired code structure analysis.

Generates a compact tree of the entire codebase showing:
- All files with their symbols (classes, functions, methods)
- Import relationships between files
- File sizes and types

This fits in ~500 tokens even for large repos, giving the model
complete structural awareness without reading every file.
"""
import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class FileSymbol:
    name: str
    kind: str  # "class", "function", "method", "variable"
    line: int
    args: str = ""  # For functions: "(self, x, y)"
    parent: str = ""  # For methods: parent class name


@dataclass
class FileInfo:
    path: str
    symbols: List[FileSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    line_count: int = 0
    size_bytes: int = 0


class RepoMap:
    """Generate an AST-based map of the repository."""

    SKIP_DIRS = {
        '.git', 'node_modules', '__pycache__', 'venv', '.venv',
        'dist', 'build', '.next', 'data', '.mypy_cache', '.cache',
        'coverage', '.pytest_cache', 'eggs',
    }

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self._file_cache: Dict[str, FileInfo] = {}

    def _parse_python_file(self, filepath: str) -> FileInfo:
        """Parse a Python file using AST to extract symbols."""
        rel_path = os.path.relpath(filepath, self.workspace_dir)
        info = FileInfo(path=rel_path)

        try:
            stat = os.stat(filepath)
            info.size_bytes = stat.st_size
        except OSError:
            return info

        try:
            with open(filepath, 'r', errors='replace') as f:
                source = f.read()
            info.line_count = source.count('\n') + 1
        except Exception:
            return info

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return info

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    info.imports.append(node.module)
            elif isinstance(node, ast.ClassDef):
                info.symbols.append(FileSymbol(
                    name=node.name, kind="class", line=node.lineno,
                ))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = ", ".join(a.arg for a in item.args.args)
                        info.symbols.append(FileSymbol(
                            name=item.name, kind="method", line=item.lineno,
                            args=f"({args})", parent=node.name,
                        ))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = ", ".join(a.arg for a in node.args.args)
                info.symbols.append(FileSymbol(
                    name=node.name, kind="function", line=node.lineno,
                    args=f"({args})",
                ))

        return info

    def _parse_simple_file(self, filepath: str) -> FileInfo:
        """Parse a non-Python file for basic info."""
        rel_path = os.path.relpath(filepath, self.workspace_dir)
        info = FileInfo(path=rel_path)
        try:
            stat = os.stat(filepath)
            info.size_bytes = stat.st_size
            with open(filepath, 'r', errors='replace') as f:
                info.line_count = sum(1 for _ in f)
        except Exception:
            pass
        return info

    def scan(self) -> Dict[str, FileInfo]:
        """Scan the entire repository and build the map."""
        self._file_cache.clear()

        for root, dirs, files in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in {'.py', '.ts', '.tsx', '.js', '.jsx', '.yaml', '.yml',
                               '.toml', '.json', '.md', '.rs', '.go'}:
                    continue

                filepath = os.path.join(root, fname)
                if ext == '.py':
                    info = self._parse_python_file(filepath)
                else:
                    info = self._parse_simple_file(filepath)

                self._file_cache[info.path] = info

        return self._file_cache

    def generate_map(self, max_tokens: int = 2000) -> str:
        """Generate a compact text map of the repository."""
        if not self._file_cache:
            self.scan()

        lines = ["# Repository Map\n"]

        # Group files by directory
        dirs: Dict[str, List[FileInfo]] = {}
        for path, info in sorted(self._file_cache.items()):
            dir_name = os.path.dirname(path) or "."
            dirs.setdefault(dir_name, []).append(info)

        for dir_name, files in sorted(dirs.items()):
            lines.append(f"\n## {dir_name}/")
            for fi in files:
                fname = os.path.basename(fi.path)
                lines.append(f"  {fname} ({fi.line_count}L)")

                for sym in fi.symbols:
                    if sym.kind == "class":
                        lines.append(f"    class {sym.name}")
                    elif sym.kind == "method":
                        lines.append(f"      .{sym.name}{sym.args}")
                    elif sym.kind == "function":
                        lines.append(f"    def {sym.name}{sym.args}")

        result = "\n".join(lines)

        # Truncate if too long (estimate ~4 chars per token)
        max_chars = max_tokens * 4
        if len(result) > max_chars:
            result = result[:max_chars] + "\n... (truncated)"

        return result

    def get_file_context(self, filepath: str) -> Optional[str]:
        """Get the context for a specific file (its imports and related files)."""
        if not self._file_cache:
            self.scan()

        info = self._file_cache.get(filepath)
        if not info:
            return None

        lines = [f"# Context for {filepath}\n"]
        lines.append(f"Lines: {info.line_count}, Size: {info.size_bytes} bytes\n")

        if info.symbols:
            lines.append("## Symbols:")
            for sym in info.symbols:
                lines.append(f"  - {sym.kind}: {sym.name} (line {sym.line})")

        if info.imports:
            lines.append("\n## Imports:")
            for imp in info.imports[:20]:
                lines.append(f"  - {imp}")

        # Find files that import this one
        module_name = filepath.replace('/', '.').replace('.py', '')
        dependents = []
        for other_path, other_info in self._file_cache.items():
            if other_path == filepath:
                continue
            for imp in other_info.imports:
                if module_name in imp or os.path.basename(filepath).replace('.py', '') in imp:
                    dependents.append(other_path)
                    break

        if dependents:
            lines.append("\n## Imported by:")
            for dep in dependents[:10]:
                lines.append(f"  - {dep}")

        return "\n".join(lines)

    async def execute(self, **params) -> Dict:
        """Tool interface for agent integration."""
        action = params.get("action", "map")
        if action == "map":
            return {"success": True, "output": self.generate_map(max_tokens=params.get("max_tokens", 2000))}
        elif action == "context":
            filepath = params.get("file", "")
            ctx = self.get_file_context(filepath)
            return {"success": True, "output": ctx or "File not found in repo map"}
        elif action == "scan":
            files = self.scan()
            return {"success": True, "output": f"Scanned {len(files)} files"}
        return {"success": False, "error": f"Unknown action: {action}"}
