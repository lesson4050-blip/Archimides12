import sys
import io
import traceback
import base64
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ReplTool:
    """
    Isolated Python REPL execution in the Docker sandbox.
    """
    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "python_repl",
                "description": "SUPER WEAPON: Execute raw Python code safely inside the isolated Docker sandbox. Note: Execution is STATELESS. Variables do not persist between calls. If you need to persist data, write it to the workspace filesystem.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string", 
                            "description": "Python code to execute inside the sandbox container."
                        }
                    },
                    "required": ["code"]
                }
            }
        }

    async def execute(self, session_id: str, code: str) -> Dict[str, Any]:
        from backend.sandbox.singleton import sandbox_manager
        
        # Encode code to avoid bash injection breaking the command
        b64_code = base64.b64encode(code.encode("utf-8")).decode("utf-8")
        cmd = f"echo '{b64_code}' | base64 -d > /tmp/repl.py && python3 /tmp/repl.py"
        
        try:
            result = await sandbox_manager.executor.run_command(
                session_id=session_id,
                command=cmd,
                timeout=60
            )
            
            out = result.get("output", "").strip()
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Unknown execution error") or out
                }
                
            return {
                "success": True, 
                "result": out or "[Executed successfully, no output]"
            }
            
        except Exception as e:
            logger.error(f"ReplTool execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
