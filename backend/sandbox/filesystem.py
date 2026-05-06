import os
import logging
import io
import tarfile
import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

class SandboxFilesystem:
    """
    Handles file operations inside the sandbox container.
    Uses docker exec and docker cp equivalent.
    """
    WORKSPACE_ROOT = "/home/ubuntu/workspace"

    def _safe_path(self, path: str) -> str:
        """Enforce path boundaries within the workspace."""
        base = os.path.normpath(self.WORKSPACE_ROOT)
        # Handle absolute paths by stripping leading slash
        target = os.path.normpath(os.path.join(base, path.lstrip("/")))
        
        if not target.startswith(base):
            raise ValueError(f"Path traversal attempt blocked: {path}")
        return target

    def __init__(self, manager: 'SandboxManager'):
        self.manager = manager

    async def read_file(self, session_id: str, path: str, start_line: int = None, end_line: int = None) -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}
            
        try:
            # Use cat via exec_run to read
            import shlex
            safe_path = shlex.quote(path)
            
            if start_line is not None and end_line is not None:
                cmd = f"sed -n '{start_line},{end_line}p' {safe_path}"
            elif start_line is not None:
                cmd = f"tail -n +{start_line} {safe_path}"
            elif end_line is not None:
                cmd = f"head -n {end_line} {safe_path}"
            else:
                cmd = f"cat {safe_path}"
                
            loop = asyncio.get_running_loop()
            exec_res = await loop.run_in_executor(None, lambda: container.exec_run(cmd, user="ubuntu"))
            
            if exec_res.exit_code == 0:
                content = exec_res.output.decode("utf-8", errors="replace")
                return {
                    "success": True,
                    "content": content
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to read file: {exec_res.output.decode()}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def write_file(self, session_id: str, path: str, content: Any) -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}
            
        try:
            safe_path = self._safe_path(path)
            
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                else:
                    content_bytes = content
                    
                file_info = tarfile.TarInfo(name=os.path.basename(safe_path))
                file_info.size = len(content_bytes)
                tar.addfile(file_info, io.BytesIO(content_bytes))
                
            tar_stream.seek(0)
            
            dirname = os.path.dirname(safe_path)
            loop = asyncio.get_running_loop()
            if dirname:
                await loop.run_in_executor(None, lambda: container.exec_run(f"mkdir -p {dirname}", user="ubuntu"))
                
            logger.info(f"SandboxFilesystem: Writing {len(content_bytes)} bytes to {safe_path} via put_archive...")
            await loop.run_in_executor(None, lambda: container.put_archive(dirname, tar_stream))
            
            return {"success": True, "size": len(content_bytes)}
        except Exception as e:
            logger.error(f"SandboxFilesystem: Error writing file {path}: {e}")
            return {"success": False, "error": str(e)}

    async def list_files(self, session_id: str, path: str = ".") -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}
            
        try:
            import shlex
            safe_path = shlex.quote(path)
            loop = asyncio.get_running_loop()
            exec_res = await loop.run_in_executor(None, lambda: container.exec_run(f"ls -F {safe_path}", user="ubuntu", workdir="/home/ubuntu/workspace"))
            if exec_res.exit_code == 0:
                return {
                    "success": True,
                    "files": exec_res.output.decode().splitlines()
                }
            else:
                return {"success": False, "error": exec_res.output.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}
