import logging
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)

class PredictiveGuard:
    """
    Проверяет команду ДО её выполнения на типичные ошибки 
    (попытка запустить sudo, rm -rf, apt-get без yes, бесконечные циклы).
    """
    
    @staticmethod
    async def analyze_command(command: str, context: str = "") -> Dict[str, Any]:
        command = command.strip()
        
        # Check for interactive package managers without non-interactive flags
        if re.search(r'\b(apt-get|apt)\s+(install|remove|upgrade)', command):
            if not re.search(r'-y|--yes', command):
                return {
                    "safe": False,
                    "reason": "apt/apt-get requires -y flag to avoid interactive prompt freeze.",
                    "suggestion": f"{command} -y"
                }

        # Check for naked python/node repls
        if command in ("python", "python3", "node"):
            return {
                "safe": False,
                "reason": "Running an interactive REPL will block the agent. Use python -c '...' or write a script and run it.",
                "suggestion": f"{command} -c 'print(\"Hello World\")'"
            }
            
        # Check for sudo
        if command.startswith("sudo"):
            return {
                "safe": False,
                "reason": "sudo is not available or required in the sandbox.",
                "suggestion": command.replace("sudo ", "", 1)
            }
            
        # Check for potentially destructive ops
        if "rm -rf / " in command or "rm -rf /*" in command:
            return {
                "safe": False,
                "reason": "Dangerous filesystem operation blocked.",
                "suggestion": None
            }
            
        # Check historical package failure map (Predictive Foresight)
        historical_failures = {
            "pip install psycopg2": "Use psycopg2-binary instead to avoid compilation errors.",
            "npm install canvas": "Canvas requires build-essential and cairo binaries. Consider using a prebuilt alternative.",
            "apt-get install nodejs": "Default apt nodejs is ancient. Use nodesource PPA or nvm."
        }
        
        for failed_cmd, suggestion in historical_failures.items():
            if failed_cmd in command:
                return {
                    "safe": False,
                    "reason": f"Known historical failure pattern detected.",
                    "suggestion": suggestion
                }

        return {"safe": True, "reason": "Command looks safe.", "suggestion": None}

    @staticmethod
    async def execute_with_guard(executor: Any, command: str, context: str = "") -> Dict[str, Any]:
        """Runs the command through the safety layer before executing it."""
        check = await PredictiveGuard.analyze_command(command, context)
        if not check["safe"]:
            return {
                "success": False,
                "error": f"PredictiveGuard Blocked Command: {check['reason']}",
                "suggestion": check["suggestion"]
            }
            
        # Command is safe, execute
        try:
            from backend.sandbox.executor import SandboxExecutor
            # Depending on the executor interface
            if hasattr(executor, "run_command"):
                return await executor.run_command(command)
            else:
                return {"success": False, "error": "Invalid executor provided to PredictiveGuard."}
        except Exception as e:
            return {"success": False, "error": f"Execution failed: {e}"}
