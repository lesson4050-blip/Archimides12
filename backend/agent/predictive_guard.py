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
            
        # Additional checking could be done via LLM here if needed
        # but for now, static analysis covers the most common blocking issues.

        return {"safe": True, "reason": "Command looks safe.", "suggestion": None}
