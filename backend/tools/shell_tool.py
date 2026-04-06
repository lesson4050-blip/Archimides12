from typing import Dict, Any, Optional
from backend.sandbox.executor import SandboxExecutor

class ShellTool:
    """
    Executes shell commands in the sandbox.
    """
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "shell",
                "description": "Executes a bash command in the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["exec"]},
                        "command": {"type": "string", "description": "The command to execute"}
                    },
                    "required": ["action", "command"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, command: Optional[str] = None, timeout: int = 60, **kwargs) -> Dict[str, Any]:
        if action == "run":
            action = "exec"
            
        if action == "exec":
            if not command:
                return {"success": False, "error": "Command is required"}
            # If command ends with & or starts with nohup, it's background — don't wait for output
            is_background = command.strip().endswith(' &') or command.strip().startswith('nohup ')
            if is_background:
                result = await self.executor.run_command(session_id, command.strip(), timeout=10)
                return {"success": True, "output": f"Background process started. {result.get('output', '')}"}
                
            result = await self.executor.run_command(session_id, command, timeout=timeout)
            output = result.get("output", "")
            if isinstance(output, str) and len(output) > 2000:
                result["output"] = output[:2000] + "\n...[truncated]"
            return result
        
        elif action == "view":
            # In MVP, 'view' might just return a generic message or last output
            # RealManus has a persistent shell session.
            return {"success": True, "output": "Terminal view is streaming in real-time to the 'Actions' tab."}
        
        elif action == "wait":
            seconds = kwargs.get("seconds", 1)
            import asyncio
            await asyncio.sleep(seconds)
            return {"success": True, "output": f"Waited {seconds} seconds."}
            
        elif action == "kill":
            pid = kwargs.get("pid")
            if not pid:
                return {"success": False, "error": "PID is required for 'kill' action."}
            return await self.executor.run_command(session_id, f"kill -9 {pid}")
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
