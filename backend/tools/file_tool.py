import os
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
                "description": "Performs file operations (read, write, list) in the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["read", "write", "append", "edit", "view"]},
                        "path": {"type": "string", "description": "Path to the file or directory"},
                        "content": {"type": "string", "description": "Content for write/append"},
                        "old_string": {"type": "string", "description": "String to replace (for edit)"},
                        "new_string": {"type": "string", "description": "Replacement string (for edit)"}
                    },
                    "required": ["action", "path"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, path: str, content: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        if action == "read":
            return await self.filesystem.read_file(session_id, path)
            
        elif action == "write":
            if content is None:
                return {"success": False, "error": "Content is required for 'write' action."}
            return await self.filesystem.write_file(session_id, path, content)
            
        elif action == "append":
            if content is None:
                return {"success": False, "error": "Content is required for 'append' action."}
            # Simplified append: read, then write back
            read_res = await self.filesystem.read_file(session_id, path)
            old_content = read_res.get("content", "")
            return await self.filesystem.write_file(session_id, path, old_content + content)
            
        elif action == "edit":
            old_string = kwargs.get("old_string")
            new_string = kwargs.get("new_string")
            if not old_string or not new_string:
                return {"success": False, "error": "old_string and new_string are required for 'edit' action."}
            
            read_res = await self.filesystem.read_file(session_id, path)
            if not read_res["success"]:
                return read_res
                
            file_content = read_res["content"]
            if old_string not in file_content:
                return {"success": False, "error": f"String '{old_string}' not found in file."}
                
            new_content = file_content.replace(old_string, new_string)
            return await self.filesystem.write_file(session_id, path, new_content)
            
        elif action == "view":
            return await self.filesystem.list_files(session_id, path)
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
