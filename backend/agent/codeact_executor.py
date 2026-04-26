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
        max_iterations: int = 15,
    ) -> Dict[str, Any]:
        """
        CodeAct execution loop.
        The agent writes Python code, executes it, observes output,
        and iterates until the task is solved or iterations exhausted.
        """
        history = []
        
        # Strong CodeAct system prompt
        system_prompt = (
            "You are CodeAct — an expert autonomous coding agent.\n"
            "You solve tasks by writing and executing Python code in a REPL.\n\n"
            "RULES:\n"
            "1. ALWAYS respond with executable Python code wrapped in ```python blocks.\n"
            "2. Use print() to show results — you can only see printed output.\n"
            "3. After seeing output, analyze it and write the NEXT code block.\n"
            "4. If code fails, fix the specific error — don't rewrite from scratch.\n"
            "5. When task is done, write: print('TASK_COMPLETE: <result summary>')\n"
            "6. Available: standard library + requests + numpy + pandas + subprocess.\n"
            "7. For file operations: use open(), pathlib, os — not shell commands.\n"
            "8. For git operations: use subprocess.run(['git', ...]).\n\n"
            "NEVER explain what you'll do. Write the code immediately."
        )
        
        if context:
            history.append({"role": "system", "content": system_prompt})
            history.append({"role": "user", "content": f"Context:\n{context}\n\nTask: {task}"})
        else:
            history.append({"role": "system", "content": system_prompt})
            history.append({"role": "user", "content": task})
        
        all_outputs = []
        
        for iteration in range(max_iterations):
            if websocket_send:
                await websocket_send({
                    "type": "thought",
                    "content": f"🔁 CodeAct iteration {iteration + 1}/{max_iterations}"
                })
            
            # Generate next code block
            response = await self.router.generate(
                messages=history,
                task_hint="execute"
            )
            
            agent_response = response.get("text", "")
            if not agent_response:
                break
            
            history.append({"role": "assistant", "content": agent_response})
            
            # Extract Python code blocks
            import re
            code_blocks = re.findall(
                r'```python\n(.*?)```',
                agent_response,
                re.DOTALL
            )
            
            if not code_blocks:
                # No code block — might be final text answer
                if "TASK_COMPLETE" in agent_response or iteration > 2:
                    return {
                        "success": True,
                        "output": agent_response,
                        "iterations": iteration + 1,
                        "all_outputs": all_outputs
                    }
                # Nudge agent to write code
                history.append({
                    "role": "user",
                    "content": "Write executable Python code to continue. Wrap it in ```python blocks."
                })
                continue
            
            # Execute all code blocks
            execution_results = []
            for code in code_blocks:
                exec_result = await self._execute_code_safe(
                    code, session_id, websocket_send
                )
                execution_results.append(exec_result)
                all_outputs.append(exec_result)
                
                if websocket_send:
                    status = "✅" if exec_result["success"] else "❌"
                    await websocket_send({
                        "type": "thought",
                        "content": f"{status} Code output: {exec_result['output'][:200]}"
                    })
            
            # Check if task is complete
            combined_output = "\n".join(r["output"] for r in execution_results)
            if "TASK_COMPLETE" in combined_output:
                final = combined_output.split("TASK_COMPLETE:")[-1].strip()
                return {
                    "success": True,
                    "output": final or combined_output,
                    "iterations": iteration + 1,
                    "all_outputs": all_outputs
                }
            
            # Add execution results to history for next iteration
            history.append({
                "role": "user",
                "content": f"Execution output:\n{combined_output}\n\nContinue solving the task."
            })
        
        # Hit iteration limit
        last_output = all_outputs[-1]["output"] if all_outputs else "No output"
        return {
            "success": False,
            "output": f"Iteration limit reached. Last output:\n{last_output}",
            "iterations": max_iterations,
            "all_outputs": all_outputs
        }

    async def _execute_code_safe(
        self,
        code: str,
        session_id: str,
        websocket_send=None,
    ) -> Dict[str, Any]:
        """Execute Python code safely via sandbox."""
        try:
            from backend.sandbox.singleton import sandbox_manager
            result = await sandbox_manager.executor.execute_code(
                code=code,
                session_id=session_id,
                timeout=30
            )
            return {
                "success": result.get("success", True),
                "output": str(result.get("output", result.get("stdout", "")))[:2000],
                "error": result.get("error", result.get("stderr", ""))
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Execution error: {e}",
                "error": str(e)
            }
