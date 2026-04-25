"""
CodeAct Executor — агент пишет Python-код как действие.
Вместо: {"tool": "shell", "command": "ls -la"}
Пишет:  import os; print(os.listdir('.'))

Код выполняется в изолированной среде.
Результат (stdout + stderr) возвращается агенту.
Архитектура используется в OpenHands CodeAct v3
(68.4% SWE-bench Verified).
"""
import asyncio
import logging
import sys
import traceback
from io import StringIO
from typing import Dict, Any, Optional
from contextlib import redirect_stdout, redirect_stderr

logger = logging.getLogger(__name__)

CODEACT_SYSTEM_PROMPT = """You are Archimedes CodeAct Agent.
You solve tasks by writing and executing Python code.

RULES:
1. To perform ANY action, write Python code and wrap it in:
   <execute_python>
   # your code here
   result = do_something()
   print(result)
   </execute_python>

2. The code runs in a real Python environment with access to:
   - os, subprocess, pathlib, json, re, requests, httpx
   - All installed packages
   - The current workspace directory

3. After execution, you see stdout + stderr.
   Use the output to decide next step.

4. For file operations: use open(), pathlib.Path
5. For shell: use subprocess.run()
6. For web requests: use httpx (async) or requests (sync)

7. Think step by step. One code block per action.
   Read output. Then decide next action.

8. When task is complete, write:
   <task_complete>
   Summary of what was accomplished.
   </task_complete>

Never use JSON tool calls. Only Python code blocks."""


class CodeActExecutor:
    """
    Executes tasks using CodeAct paradigm.
    Agent writes Python → we execute → agent reads output → repeat.
    """

    def __init__(self, router, max_iterations: int = 30):
        self.router = router
        self.max_iterations = max_iterations

    async def execute(
        self,
        task: str,
        context: str = "",
        session_id: str = "default",
        websocket_send=None,
    ) -> Dict[str, Any]:

        messages = [
            {"role": "system", "content": CODEACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"TASK: {task}\n"
                    + (f"\nCONTEXT: {context}" if context else "")
                )
            }
        ]

        iterations = 0
        execution_log = []

        while iterations < self.max_iterations:
            iterations += 1

            # Get agent's next action
            response = await self.router.generate(
                messages=messages,
                task_hint="think",
                temperature=0.2,
            )
            agent_text = response.get("text", "").strip()

            if websocket_send:
                await websocket_send({
                    "type": "thought",
                    "thought_type": "codeact",
                    "content": agent_text[:200],
                })

            # Check if task is complete
            if "<task_complete>" in agent_text:
                summary_start = agent_text.find("<task_complete>") + 15
                summary_end = agent_text.find("</task_complete>")
                summary = agent_text[summary_start:summary_end].strip()
                return {
                    "success": True,
                    "output": summary,
                    "iterations": iterations,
                    "execution_log": execution_log,
                }

            # Extract and execute Python code
            if "<execute_python>" in agent_text:
                code_start = agent_text.find("<execute_python>") + 16
                code_end = agent_text.find("</execute_python>")
                if code_end > code_start:
                    code = agent_text[code_start:code_end].strip()
                    stdout, stderr, error = await self._execute_code(code)

                    execution_log.append({
                        "iteration": iterations,
                        "code": code[:300],
                        "stdout": stdout[:500],
                        "stderr": stderr[:200],
                    })

                    # Feed result back to agent
                    messages.append({
                        "role": "assistant",
                        "content": agent_text
                    })
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Execution result:\n"
                            f"STDOUT:\n{stdout[:2000]}\n"
                            + (f"STDERR:\n{stderr[:500]}\n" if stderr else "")
                            + (f"ERROR: {error}\n" if error else "")
                            + "\nContinue with next action or mark complete."
                        )
                    })
                    continue

            # No code block — agent gave a text response
            messages.append({"role": "assistant", "content": agent_text})
            # Prompt to write code
            messages.append({
                "role": "user",
                "content": (
                    "Please write Python code to take the next action. "
                    "Use <execute_python>...</execute_python> tags."
                )
            })

        return {
            "success": False,
            "output": "Max iterations reached",
            "iterations": iterations,
            "execution_log": execution_log,
        }

    async def _execute_code(
        self, code: str
    ) -> tuple[str, str, Optional[str]]:
        """Execute Python code safely, capture output."""
        stdout_buf = StringIO()
        stderr_buf = StringIO()
        error = None

        try:
            # Implement strict import filtering
            import builtins
            original_import = builtins.__import__
            
            # List of forbidden modules
            forbidden_modules = {'ctypes', 'pty', 'tty', 'resource', 'multiprocessing'}
            
            def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                root_module = name.split('.')[0]
                if root_module in forbidden_modules:
                    raise ImportError(f"Import of '{name}' is forbidden by security policy.")
                return original_import(name, globals, locals, fromlist, level)
            
            safe_builtins = {k: v for k, v in builtins.__dict__.items()}
            safe_builtins['__import__'] = safe_import
            
            # Create isolated namespace
            namespace = {
                "__builtins__": safe_builtins,
                "asyncio": asyncio,
            }
            # Import common modules
            exec(
                "import os, sys, json, re, pathlib, subprocess, "
                "shutil, tempfile\n"
                "from pathlib import Path",
                namespace
            )

            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(code, namespace)

        except Exception as e:
            error = f"{type(e).__name__}: {e}\n"
            error += traceback.format_exc()[-500:]

        return (
            stdout_buf.getvalue(),
            stderr_buf.getvalue(),
            error
        )
