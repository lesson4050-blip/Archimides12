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
            logger.info("E2BSandbox initialized with E2B.")
            try:
                import e2b
            except ImportError:
                logger.warning("e2b package not found. Falling back to local.")
                self.use_e2b = False
        else:
            logger.info("E2B_API_KEY not set. E2BSandbox falling back to subprocess.")

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
            from e2b import Sandbox
            with Sandbox(api_key=self.api_key) as sandbox:
                process = sandbox.process.start(cmd, timeout=timeout)
                out = process.stdout
                err = process.stderr
                code = process.exit_code
                return out, err, code
        except Exception as e:
            logger.error(f"E2B execution failed: {e}")
            return "", str(e), 1
