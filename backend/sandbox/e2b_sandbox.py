import os
import subprocess
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class E2BSandbox:
    """
    E2B Sandbox integration.
    Falls back to local subprocess if E2B_API_KEY is not set.
    """
    def __init__(self):
        self.api_key = os.getenv("E2B_API_KEY")
        self.use_e2b = bool(self.api_key)
        if self.use_e2b:
            try:
                import e2b_code_interpreter
                logger.info("E2B v2 (e2b_code_interpreter) available")
            except ImportError:
                try:
                    import e2b
                    logger.info("E2B v1 available")
                except ImportError:
                    logger.warning(
                        "Neither e2b nor e2b_code_interpreter installed. "
                        "Run: pip install e2b-code-interpreter"
                    )
                    self.use_e2b = False
        else:
            logger.info("E2B_API_KEY not set — using local subprocess")

    def run_command(self, cmd: str, timeout: int = 60) -> Tuple[str, str, int]:
        if self.use_e2b:
            return self._run_e2b(cmd, timeout)
        return self._run_local(cmd, timeout)

    def _run_local(self, cmd: str, timeout: int) -> Tuple[str, str, int]:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout expired", 124
        except Exception as e:
            return "", str(e), 1

    def _run_e2b(self, cmd: str, timeout: int) -> Tuple[str, str, int]:
        try:
            from e2b_code_interpreter import Sandbox
            with Sandbox(api_key=self.api_key) as sbx:
                result = sbx.run_code(cmd)
                stdout = "\n".join(
                    str(r) for r in (result.logs.stdout or [])
                )
                stderr = "\n".join(
                    str(r) for r in (result.logs.stderr or [])
                )
                error_msg = ""
                if result.error:
                    error_msg = str(result.error)
                    return stdout, stderr + error_msg, 1
                return stdout, stderr, 0
        except ImportError:
            # Fallback to e2b v1 API
            try:
                from e2b import Sandbox
                with Sandbox(api_key=self.api_key) as sandbox:
                    process = sandbox.process.start(cmd)
                    process.wait()
                    return (
                        process.stdout or "",
                        process.stderr or "",
                        process.exit_code or 0
                    )
            except Exception as e2:
                logger.error(f"E2B v1 also failed: {e2}")
                return "", str(e2), 1
        except Exception as e:
            logger.error(f"E2B v2 execution failed: {e}")
            return self._run_local(cmd, timeout)
