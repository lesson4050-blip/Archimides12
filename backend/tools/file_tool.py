from typing import Dict, Any, Optional
from backend.sandbox.filesystem import SandboxFilesystem

class FileTool:
    """
    Handles file operations in the sandbox.
    """
    def __init__(self, filesystem: SandboxFilesystem):
        self.filesystem = filesystem

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "file",
                "description": "Performs file operations (read, write, append, edit, view) in the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["read", "write", "append", "edit", "view"]},
                        "path": {"type": "string", "description": "Path to the file or directory"},
                        "content": {"type": "string", "description": "Content for write/append, or new content for edit"},
                        "start_line": {"type": "integer", "description": "Start line number (1-indexed) for read or edit"},
                        "end_line": {"type": "integer", "description": "End line number (1-indexed) for read or edit"},
                        "old_string": {"type": "string", "description": "Deprecated: string to replace (for edit)"},
                        "new_string": {"type": "string", "description": "Deprecated: replacement string (for edit)"}
                    },
                    "required": ["action", "path"]
                }
            }
        }

    def _safe_path(self, path: str, workspace: str = None) -> tuple[bool, str]:
        """
        Validate path is safe and within workspace boundaries.
        Returns (is_safe, resolved_path or error_message).
        """
        import os
        
        # Get absolute path without resolving symlinks first for initial check
        abs_path = os.path.abspath(path)
        
        # Resolve all symlinks to get the REAL location on disk
        try:
            resolved = os.path.realpath(abs_path)
        except Exception as e:
            return False, f"Invalid path or permission error: {str(e)}"
        
        # Block system paths (more comprehensive list)
        BLOCKED_PREFIXES = [
            "/etc/", "/sys/", "/proc/", "/dev/",
            "/usr/bin/", "/usr/sbin/", "/bin/", "/sbin/",
            "/usr/lib/", "/usr/lib64/", "/lib/", "/lib64/",
            "/var/", "/root/", "/boot/", "/opt/",
            "C:\\Windows\\", "C:\\System32\\", "C:\\Program Files\\", "C:\\Users\\"
        ]
        
        for prefix in BLOCKED_PREFIXES:
            if resolved.startswith(prefix) or resolved.lower().startswith(prefix.lower()):
                # Allow access if it's explicitly part of the workspace (e.g. if workspace is in /opt/)
                # but generally these are off-limits.
                return False, f"Access to system path blocked: {prefix}"
        
        # Enforce Workspace Root if provided
        workspace_root = workspace or os.getcwd()
        resolved_workspace = os.path.realpath(workspace_root)
        
        if not resolved.startswith(resolved_workspace):
            # Check if it's trying to escape via symlink or ..
            return False, f"Security violation: Path {path} (resolved to {resolved}) is outside the workspace root {resolved_workspace}"

        # Block path traversal in the raw input as an extra layer
        if ".." in path.replace("\\", "/").split("/"):
            return False, "Path traversal (../) is explicitly forbidden for security reasons."
        
        return True, resolved

    async def _auto_snapshot(self, path: str, action: str):
        """Creates an auto-backup snapshot before editing a file. Uses docker exec to run git inside sandbox if possible, or falls back to local git but with correct cwd."""
        import subprocess
        import os
        try:
            # We want to run git in the directory of the file, not in the agent's CWD
            target_dir = os.path.dirname(os.path.abspath(path))
            if not target_dir or not os.path.exists(target_dir):
                target_dir = os.path.dirname(path) or "."
            
            # Check if it's a git repo safely
            git_check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=target_dir, capture_output=True, text=True)
            if git_check.returncode == 0 and git_check.stdout.strip() == "true":
                msg = f"Auto-backup before {action} on {path}"
                subprocess.run(["git", "add", os.path.abspath(path)], cwd=target_dir, capture_output=True)
                subprocess.run(["git", "commit", "-m", msg], cwd=target_dir, capture_output=True)
        except Exception as e:
            pass  # Fail silently if git fails, don't block the write

    async def execute(self, session_id: str, action: str, path: str, content: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # Validation for ALL actions
        is_safe, result_path = self._safe_path(path)
        if not is_safe:
            return {"success": False, "error": result_path}
        
        # Normalize path for sandbox
        path = result_path.replace("\\", "/")

        if action == "read":
            start_line = kwargs.get("start_line")
            end_line = kwargs.get("end_line")
            return await self.filesystem.read_file(session_id, path, start_line, end_line)
            
        elif action == "write":
            if content is None:
                return {"success": False, "error": "Content is required for 'write' action."}
            await self._auto_snapshot(path, "write")
            res = await self.filesystem.write_file(session_id, path, content)
            if res.get("success") and path.endswith(".py"):
                from backend.agent.lsp_client import LSPClient
                diagnostics = LSPClient().validate_file(path)
                if diagnostics:
                    res["warnings"] = [d.get("message", "") for d in diagnostics]
                    res["message"] = "File written but contains syntax warnings."
            return res
            
        elif action == "append":
            if content is None:
                return {"success": False, "error": "Content is required for 'append' action."}
            await self._auto_snapshot(path, "append")
            read_res = await self.filesystem.read_file(session_id, path)
            old_content = read_res.get("content", "")
            return await self.filesystem.write_file(session_id, path, old_content + content)
            
        elif action == "edit":
            await self._auto_snapshot(path, "edit")
            
            # Support both SOTA start_line/end_line and legacy old_string/new_string
            start_line = kwargs.get("start_line")
            end_line = kwargs.get("end_line")
            
            read_res = await self.filesystem.read_file(session_id, path)
            if not read_res["success"]:
                return read_res
                
            file_content = read_res["content"]
            
            if start_line is not None and end_line is not None and content is not None:
                # Line-based replacement (robust)
                lines = file_content.split("\n")
                # Ensure valid bounds
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                
                # Replace the slice
                lines[start_idx:end_idx] = content.split("\n")
                new_content = "\n".join(lines)
                res = await self.filesystem.write_file(session_id, path, new_content)
                if res.get("success") and path.endswith(".py"):
                    from backend.agent.lsp_client import LSPClient
                    diagnostics = LSPClient().validate_file(path)
                    if diagnostics:
                        res["warnings"] = [d.get("message", "") for d in diagnostics]
                        res["message"] = "File edited but contains syntax warnings."
                return res
                
            else:
                # Legacy string replacement
                old_string = kwargs.get("old_string")
                new_string = kwargs.get("new_string")
                if not old_string or not new_string:
                    return {"success": False, "error": "Either start_line/end_line/content or old_string/new_string required for 'edit'."}
                
                if old_string not in file_content:
                    # Try a softer match (e.g. ignoring leading/trailing whitespace differences)
                    import re
                    # Very basic fallback: maybe just whitespace mismatch
                    soft_old = re.sub(r'\s+', ' ', old_string.strip())
                    soft_file = re.sub(r'\s+', ' ', file_content)
                    if soft_old in soft_file:
                        return {"success": False, "error": f"String not found exactly due to whitespace/indentation. Use start_line/end_line with content instead."}
                    return {"success": False, "error": f"String '{old_string}' not found in file."}
                    
                new_content = file_content.replace(old_string, new_string)
                res = await self.filesystem.write_file(session_id, path, new_content)
                if res.get("success") and path.endswith(".py"):
                    from backend.agent.lsp_client import LSPClient
                    diagnostics = LSPClient().validate_file(path)
                    if diagnostics:
                        res["warnings"] = [d.get("message", "") for d in diagnostics]
                        res["message"] = "File edited but contains syntax warnings."
                return res
            
        elif action == "view":
            return await self.filesystem.list_files(session_id, path)
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
