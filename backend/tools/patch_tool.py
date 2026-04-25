"""
Git Patch Tool — apply and generate unified diffs.
Critical for SWE-bench style tasks (apply patches to codebases).
"""
import subprocess
import tempfile
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PatchTool:
    """Apply and generate git-style unified diffs."""
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "patch",
                "description": (
                    "Apply a unified diff patch to a file, or generate a diff "
                    "between two versions of a file. Use for precise code edits "
                    "without rewriting entire files."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["apply", "diff", "preview"],
                            "description": (
                                "apply: apply a patch string to target file(s). "
                                "diff: generate diff between original and modified. "
                                "preview: show what patch would change without applying."
                            )
                        },
                        "patch": {
                            "type": "string",
                            "description": "Unified diff patch string (for apply/preview)"
                        },
                        "original": {
                            "type": "string", 
                            "description": "Original file content (for diff action)"
                        },
                        "modified": {
                            "type": "string",
                            "description": "Modified file content (for diff action)"
                        },
                        "target_path": {
                            "type": "string",
                            "description": "File path to apply patch to"
                        }
                    },
                    "required": ["action"]
                }
            }
        }
    
    async def execute(self, action: str, patch: str = None,
                      original: str = None, modified: str = None,
                      target_path: str = None, **kwargs) -> Dict[str, Any]:
        try:
            if action == "diff":
                if not original or not modified:
                    return {"success": False, "error": "diff requires original and modified"}
                with tempfile.NamedTemporaryFile(mode='w', suffix='.orig', delete=False) as f1:
                    f1.write(original)
                    f1_path = f1.name
                with tempfile.NamedTemporaryFile(mode='w', suffix='.new', delete=False) as f2:
                    f2.write(modified)
                    f2_path = f2.name
                try:
                    result = subprocess.run(
                        ["diff", "-u", f1_path, f2_path],
                        capture_output=True, text=True
                    )
                    return {"success": True, "output": result.stdout or "(no differences)"}
                finally:
                    os.unlink(f1_path)
                    os.unlink(f2_path)
                    
            elif action in ("apply", "preview"):
                if not patch:
                    return {"success": False, "error": "apply/preview requires patch"}
                dry_run = ["--dry-run"] if action == "preview" else []
                with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as pf:
                    pf.write(patch)
                    patch_path = pf.name
                try:
                    result = subprocess.run(
                        ["patch", "-p1"] + dry_run + ["-i", patch_path],
                        capture_output=True, text=True,
                        cwd=os.getcwd()
                    )
                    success = result.returncode == 0
                    output = result.stdout + result.stderr
                    return {"success": success, "output": output}
                finally:
                    os.unlink(patch_path)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"PatchTool error: {e}")
            return {"success": False, "error": str(e)}
