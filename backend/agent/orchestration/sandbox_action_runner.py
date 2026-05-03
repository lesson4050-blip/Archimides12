import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SandboxActionRunner:
    """
    Executes full python scripts directly in the sandbox to bypass the JSON tool-call bottleneck.
    "Executable Actions" architecture (Phase 8).
    """
    def __init__(self, executor):
        self.executor = executor

    async def execute_agentic_script(self, script_code: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Executes the provided Python script in the secure sandbox.
        The script should print or return its final output.
        """
        logger.info(f"Executing agentic script ({len(script_code)} bytes)...")
        
        # We wrap the script in a standard execution harness to catch outputs and errors.
        harness = f"""
import sys
import io
import traceback

__out = io.StringIO()
sys.stdout = __out
sys.stderr = __out

try:
{self._indent(script_code)}
    result_code = 0
except Exception as e:
    traceback.print_exc(file=__out)
    result_code = 1

__out_val = __out.getvalue()
print(f"---RESULT_CODE:{result_code}---")
print(__out_val)
"""
        
        # We use the existing sandbox executor to run the harness.
        # Assuming executor has a run_code or execute_command method.
        # Here we simulate writing to a temp file and running it.
        try:
            res = await self.executor.execute_command(
                command=["python", "-c", harness],
                timeout=timeout
            )
            
            stdout = res.get("stdout", "")
            stderr = res.get("stderr", "")
            output = stdout + stderr
            
            if "---RESULT_CODE:1---" in output or res.get("exit_code", 0) != 0:
                return {"success": False, "error": output.replace("---RESULT_CODE:1---", "").strip()}
            else:
                return {"success": True, "result": output.replace("---RESULT_CODE:0---", "").strip()}
                
        except Exception as e:
            logger.error(f"SandboxActionRunner failed: {e}")
            return {"success": False, "error": str(e)}

    def _indent(self, code: str) -> str:
        return "\n".join("    " + line for line in code.splitlines())
