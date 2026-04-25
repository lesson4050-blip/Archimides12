import subprocess
import logging
from typing import List, Dict, Any, Optional
import os

try:
    import jedi
    JEDI_AVAILABLE = True
except ImportError:
    JEDI_AVAILABLE = False

logger = logging.getLogger(__name__)

class LSPClient:
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = workspace_dir

    def validate_file(self, filepath: str) -> List[Dict[str, Any]]:
        if not filepath.endswith(".py"):
            return []
            
        logger.info(f"LSP: Validating {filepath}")
        diagnostics = []
        try:
            # Syntax check using py_compile as fallback for full LSP
            res = subprocess.run(["python", "-m", "py_compile", filepath], capture_output=True, text=True)
            if res.returncode != 0:
                diagnostics.append({"severity": "ERROR", "message": res.stderr.strip()})
        except Exception as e:
            diagnostics.append({"severity": "ERROR", "message": str(e)})
            
        return diagnostics

    def get_completions(self, source_code: str, line: int, column: int, path: str = "") -> List[Dict[str, Any]]:
        """
        Get code completions at a specific position.
        line: 1-based
        column: 0-based
        """
        if not JEDI_AVAILABLE:
            logger.warning("Jedi is not installed, auto-completion is unavailable.")
            return []
            
        try:
            script = jedi.Script(source_code, path=path if path else None)
            completions = script.complete(line, column)
            result = []
            for c in completions:
                result.append({
                    "name": c.name,
                    "type": c.type,
                    "description": c.description,
                    "docstring": c.docstring()
                })
            return result
        except Exception as e:
            logger.error(f"Error getting completions: {e}")
            return []

    def get_signatures(self, source_code: str, line: int, column: int, path: str = "") -> List[Dict[str, Any]]:
        """
        Get signature help at a specific position.
        line: 1-based
        column: 0-based
        """
        if not JEDI_AVAILABLE:
            return []
            
        try:
            script = jedi.Script(source_code, path=path if path else None)
            signatures = script.get_signatures(line, column)
            result = []
            for sig in signatures:
                params = [{"name": p.name, "description": p.description} for p in sig.params]
                result.append({
                    "name": sig.name,
                    "params": params,
                    "docstring": sig.docstring()
                })
            return result
        except Exception as e:
            logger.error(f"Error getting signatures: {e}")
            return []
