"""
TDD Executor: Test-Driven Development Engine.
Forces the agent to write a test first, then the code,
and iterates until the test passes.
"""
import asyncio
import logging
import uuid
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TDDExecutor:
    """
    Wraps standard task execution in a TDD loop for code tasks.
    """
    def __init__(self, router, sandbox_executor):
        self.router = router
        self.sandbox = sandbox_executor

    async def execute_tdd(
        self,
        task: str,
        session_id: str,
        websocket_send: Optional[callable] = None
    ) -> str:
        """
        1. Write test
        2. Write code
        3. Run test
        4. Fix until pass (max 3 tries)
        """
        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": "🧪 Запуск TDD-цикла (Test-Driven Development)...",
                "agent": "tdd_executor"
            })

        # Step 1: Write Test First
        test_prompt = f"""
Task: {task}
Write a pytest script that verifies this task is implemented correctly.
Output ONLY the python code for the test, wrapped in ```python
Use standard libraries or pytest.
Assume the target code will be in a file named implementation.py
"""
        res_test = await self.router.generate(
            messages=[{"role": "user", "content": test_prompt}],
            task_hint="think"
        )
        test_code = self._extract_code(res_test.get("text", ""))
        
        if not test_code:
            return "[TDD] Failed to generate test. Falling back to normal execution."

        # Save test to sandbox
        safe_test = test_code.replace("'", "'\\''")
        await self.sandbox.run_command(
            session_id, f"echo '{safe_test}' > test_task.py"
        )

        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": "✅ Тесты написаны. Начинаю реализацию...",
                "agent": "tdd_executor"
            })

        # Step 2: Loop implementation
        max_attempts = 3
        current_code = ""

        # Initial implementation prompt
        impl_prompt = f"""
Task: {task}
Pass these tests:\n{test_code}
Write the implementation code for implementation.py
Output ONLY the python code, wrapped in ```python
"""
        for attempt in range(max_attempts):
            res_impl = await self.router.generate(
                messages=[{"role": "user", "content": impl_prompt}],
                task_hint="think"
            )
            current_code = self._extract_code(res_impl.get("text", ""))

            # Save implementation
            safe_impl = current_code.replace("'", "'\\''")
            await self.sandbox.run_command(
                session_id, f"echo '{safe_impl}' > implementation.py"
            )

            # Step 3: Run Test
            test_run = await self.sandbox.run_command(
                session_id, "pytest test_task.py -v"
            )
            output = test_run.get("output", "")
            
            if test_run.get("success") and "failed" not in output.lower():
                if websocket_send:
                    await websocket_send({
                        "type": "thought",
                        "content": f"🎉 TDD: Код прошел тесты (попытка {attempt+1})!",
                        "agent": "tdd_executor"
                    })
                return f"[TDD Success]\nIMPLEMENTATION:\n{current_code}\n\nTEST RUN:\n{output}"

            # Failed? Update prompt with error
            if websocket_send:
                await websocket_send({
                    "type": "thought",
                    "content": f"❌ TDD: Тесты упали. Исправление (попытка {attempt+1}/{max_attempts})...",
                    "agent": "tdd_executor"
                })

            impl_prompt = f"""
Task: {task}
Your previous code failed the tests.
TEST OUTPUT:
{output[-1500:]}

PREVIOUS CODE:
{current_code}

Fix the code. Output ONLY the python code for implementation.py wrapped in ```python
"""

        return f"[TDD Failed after {max_attempts} attempts]\nLast code:\n{current_code}"

    def _extract_code(self, text: str) -> str:
        matches = re.findall(r'```(?:python)?\n(.*?)\n```', text, re.DOTALL)
        return matches[0] if matches else text
