import re
from typing import Dict, Any

class LogAnalyzerTool:
    """
    Parses giant test outputs and logs to extract only the meaningful stack traces 
    and errors, saving the LLM from context overflow.
    """
    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "log_analyzer",
                "description": "Analyzes large text logs or pytest outputs to extract meaningful errors, tracebacks, and assertion failures without overwhelming the context limit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "log_content": {"type": "string", "description": "The raw giant log text to analyze"}
                    },
                    "required": ["log_content"]
                }
            }
        }

    async def execute(self, session_id: str, log_content: str) -> Dict[str, Any]:
        if not log_content:
            return {"success": False, "error": "log_content is empty"}
            
        lines = log_content.split('\n')
        if len(lines) < 50:
            # If it's small, don't bother truncating
            return {"success": True, "analyzed_log": log_content}
            
        important_lines = []
        in_traceback = False
        
        for idx, line in enumerate(lines):
            # Pytest / Python tracebacks
            if "Traceback (most recent call last):" in line or "ERRORS" in line or "FAILURES" in line:
                in_traceback = True
                important_lines.append("\n--- [TRACEBACK START] ---")
            
            if in_traceback:
                important_lines.append(line)
                # End of traceback heuristics
                if not line.startswith(" ") and not line.startswith("Traceback") and idx > 0 and len(important_lines) > 5:
                    if "Error:" in line or "Exception:" in line:
                        important_lines.append("--- [TRACEBACK END] ---\n")
                        in_traceback = False
            
            # Catch standalone error indicators
            elif any(indicator in line for indicator in ["AssertionError", "SyntaxError", "ValueError", "TypeError", "FAILED"]):
                important_lines.append(f"[ERROR FOUND]: {line}")
                
        # Also include the last 20 lines as they often contain the test summary
        important_lines.append("\n--- [LOG SUMMARY (LAST 20 LINES)] ---")
        important_lines.extend(lines[-20:])
        
        result_text = "\n".join(important_lines)
        
        # Prevent it from still being too huge
        if len(result_text) > 3000:
            head = result_text[:1000]
            tail = result_text[-2000:]
            result_text = head + "\n...[TRUNCATED BY LOG ANALYZER]...\n" + tail
            
        return {
            "success": True, 
            "original_length": len(log_content),
            "reduced_length": len(result_text),
            "analyzed_log": result_text
        }
