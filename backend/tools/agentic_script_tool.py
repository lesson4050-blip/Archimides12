"""
Phase 8 — Shift 1: Executable Actions (Manus-killer).
Instead of 10 JSON tool_calls, the LLM writes one Python script
that runs autonomously inside the sandbox until the goal is met.
"""
import base64
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AgenticScriptTool:
    """
    Executes a full autonomous Python script inside the Docker sandbox.
    The script has access to the workspace filesystem and can perform
    multi-step logic (loops, conditionals, file I/O) in a single call.
    """

    def __init__(self):
        pass

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "execute_agentic_script",
                "description": (
                    "NUCLEAR WEAPON: Execute a full autonomous Python script inside the sandbox. "
                    "Use this instead of multiple tool calls when the task requires loops, "
                    "conditionals, file processing, or multi-step logic. "
                    "The script runs to completion and returns stdout/stderr. "
                    "Available libraries: os, json, re, pathlib, subprocess, requests, "
                    "csv, datetime, math, collections, itertools. "
                    "Workspace is mounted at /workspace. "
                    "IMPORTANT: Print your final result to stdout — that is what gets returned."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": (
                                "Complete Python script to execute. Must be self-contained. "
                                "Print results to stdout. Use try/except for error handling."
                            )
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Max execution time in seconds (default 60, max 300)."
                        }
                    },
                    "required": ["script"]
                }
            }
        }

    async def execute(self, session_id: str, script: str, timeout: int = 60, **kwargs) -> Dict[str, Any]:
        from backend.sandbox.singleton import sandbox_manager

        timeout = min(max(timeout, 5), 300)  # Clamp 5-300s

        # Encode to avoid shell injection
        b64_script = base64.b64encode(script.encode("utf-8")).decode("utf-8")
        cmd = (
            f"echo '{b64_script}' | base64 -d > /tmp/_agentic_run.py && "
            f"cd /workspace && python3 /tmp/_agentic_run.py 2>&1"
        )

        try:
            result = await sandbox_manager.executor.run_command(
                session_id=session_id,
                command=cmd,
                timeout=timeout
            )

            out = result.get("output", "").strip()
            success = result.get("success", False)

            if not success:
                error_msg = result.get("error", "") or out
                logger.warning(f"AgenticScript failed: {error_msg[:200]}")
                return {
                    "success": False,
                    "error": error_msg[:2000]
                }

            return {
                "success": True,
                "output": out[:5000] if out else "[Script completed, no output]"
            }

        except Exception as e:
            logger.error(f"AgenticScriptTool crashed: {e}")
            return {"success": False, "error": str(e)}
