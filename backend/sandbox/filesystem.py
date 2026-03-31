import os
import logging
import io
import tarfile
import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

class SandboxFilesystem:
    """
    Handles file operations inside the sandbox container.
    Uses docker exec and docker cp equivalent.
    """
    def __init__(self, manager: 'SandboxManager'):
        self.manager = manager

    async def read_file(self, session_id: str, path: str) -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}
            
        try:
            # Use cat via exec_run to read
            # Alternatively use container.get_archive if binary, 
            # but for text file tool cat is simpler.
            loop = asyncio.get_running_loop()
            exec_res = await loop.run_in_executor(None, lambda: container.exec_run(f"cat {path}", user="ubuntu"))
            
            if exec_res.exit_code == 0:
                return {
                    "success": True,
                    "content": exec_res.output.decode("utf-8", errors="replace")
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to read file: {exec_res.output.decode()}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def write_file(self, session_id: str, path: str, content: str) -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}
            
        try:
            # Use docker cp logic (put_archive) to write files safely
            # This avoids shell escaping issues with 'echo'
            
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                content_bytes = content.encode('utf-8')
                file_info = tarfile.TarInfo(name=os.path.basename(path))
                file_info.size = len(content_bytes)
                tar.addfile(file_info, io.BytesIO(content_bytes))
                
            tar_stream.seek(0)
            
            # Ensure directory exists
            dirname = os.path.dirname(path)
            loop = asyncio.get_running_loop()
            if dirname:
                await loop.run_in_executor(None, lambda: container.exec_run(f"mkdir -p {dirname}", user="ubuntu"))
                
            await loop.run_in_executor(None, lambda: container.put_archive(dirname or "/home/ubuntu/workspace", tar_stream))
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_files(self, session_id: str, path: str = ".") -> Dict[str, Any]:
        container = await self.manager.get_container(session_id)
        if not container:
            return {"success": False, "error": "Sandbox container not available."}
            
        try:
            loop = asyncio.get_running_loop()
            exec_res = await loop.run_in_executor(None, lambda: container.exec_run(f"ls -F {path}", user="ubuntu", workdir="/home/ubuntu/workspace"))
            if exec_res.exit_code == 0:
                return {
                    "success": True,
                    "files": exec_res.output.decode().splitlines()
                }
            else:
                return {"success": False, "error": exec_res.output.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}
