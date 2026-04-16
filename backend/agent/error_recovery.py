from typing import List, Dict, Any
import logging
import datetime

logger = logging.getLogger(__name__)

class ErrorRecovery:
    """
    Handles tool retry logic and fallback strategies.
    Ensures the agent doesn't repeat the same failing command identically.
    """
    def __init__(self):
        self.tool_failure_history: List[Dict[str, Any]] = []
        self.max_retries = 3

    def record_failure(self, tool_name: str, params: Dict[str, Any], error: str):
        self.tool_failure_history.append({
            "tool": tool_name,
            "params": params,
            "error": error,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })

    def should_retry(self, tool_name: str, params: Dict[str, Any]) -> bool:
        # Check if we've reached max retries for a similar tool/params combination
        # Simplified: checking if previous failure exists for SAME params
        count = sum(1 for f in self.tool_failure_history if f["tool"] == tool_name and f["params"] == params)
        return count < self.max_retries

    def get_recovery_advice(self, tool_name: str, error: str) -> str:
        # Provide suggestions to the model on how to fix the error
        if "timeout" in error.lower():
            return "The command timed out. Try with a larger timeout or optimize the command."
        if "permission denied" in error.lower():
            return "Access denied. Use 'sudo' if necessary or check file permissions."
        if "not found" in error.lower():
            return "Command or file not found. Check if the package is installed or the path is correct."
        
        return f"Error: {error}. Try a different approach or modify parameters."
