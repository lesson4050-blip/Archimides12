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

    def _get_test_config(self, code_path: str) -> dict:
        """Get test configuration based on file language."""
        if code_path.endswith(".py"):
            return {
                "test_file": "test_task.py",
                "run_cmd": "python -m pytest test_task.py -v "
                           "--tb=short --cov=. --cov-report=term-missing",
                "impl_file": "implementation.py",
                "lang": "python"
            }
        elif code_path.endswith((".js", ".ts")):
            return {
                "test_file": "test_task.test.js",
                "run_cmd": "npx jest test_task.test.js --no-coverage",
                "impl_file": "implementation.js",
                "lang": "javascript"
            }
        return None

    async def execute_tdd(
        self,
        task: str,
        session_id: str,
        initial_code: str = "",
        code_path: str = "implementation.py",
        websocket_send: Optional[callable] = None
    ) -> str:
        """
        1. Write test
        2. Write code (or use provided initial_code)
        3. Run test
        4. Fix until pass (max 3 tries)
        """
        MAX_ITERATIONS = 3
        current_code = initial_code  # Start with provided code, don't regenerate
        filename = code_path.split("/")[-1] or "implementation.py"

        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": "🧪 Запуск TDD-цикла (Test-Driven Development)...",
                "agent": "tdd_executor"
            })

        # Write initial code to sandbox if provided
        if current_code:
            safe_code = current_code.replace("'", "'\\''")
            await self.sandbox.run_command(
                session_id,
                f"cat > /home/ubuntu/workspace/{filename} << 'ARCHEOF'\n"
                f"{current_code}\nARCHEOF"
            )

        # Step 1: Write Test First
        test_prompt = f"""
Task: {task}
{"Existing implementation:" + chr(10) + current_code[:2000] if current_code else ""}
Write a pytest script that verifies this task is implemented correctly.
Output ONLY the python code for the test, wrapped in ```python
Use standard libraries or pytest.
Assume the target code will be in a file named {filename}
"""
        res_test = await self.router.generate(
            messages=[{"role": "user", "content": test_prompt}],
            task_hint="think"
        )
        test_code = self._extract_code(res_test.get("text", ""))
        
        if not test_code:
            return "[TDD] Failed to generate test. Falling back to normal execution."

        # Save test to sandbox using heredoc for safety
        await self.sandbox.run_command(
            session_id,
            f"cat > /home/ubuntu/workspace/test_task.py << 'ARCHEOF'\n"
            f"{test_code}\nARCHEOF"
        )

        if websocket_send:
            await websocket_send({
                "type": "thought",
                "content": "✅ Тесты написаны. Начинаю реализацию...",
                "agent": "tdd_executor"
            })

        # Step 2: Loop implementation
        # If we have initial_code, skip first generation
        impl_prompt = f"""
Task: {task}
Pass these tests:\n{test_code}
Write the implementation code for {filename}
Output ONLY the python code, wrapped in ```python
"""
        for attempt in range(MAX_ITERATIONS):
            if not current_code:
                # Generate implementation only if we don't have code yet
                res_impl = await self.router.generate(
                    messages=[{"role": "user", "content": impl_prompt}],
                    task_hint="think"
                )
                current_code = self._extract_code(res_impl.get("text", ""))

                # Save implementation using heredoc
                await self.sandbox.run_command(
                    session_id,
                    f"cat > /home/ubuntu/workspace/{filename} << 'ARCHEOF'\n"
                    f"{current_code}\nARCHEOF"
                )

            # Auto-install missing packages before running tests
            test_output = ""
            for pip_attempt in range(2):
                # Pre-flight: lint the code
                if pip_attempt == 0:
                    if filename.endswith(".py"):
                        lint_result = await self.sandbox.run_command(
                            session_id,
                            f"python -m py_compile /home/ubuntu/workspace/{filename} "
                            f"2>&1 || true",
                            timeout=10
                        )
                        lint_output = lint_result.get("output", "")
                        if "SyntaxError" in lint_output:
                            # Fix syntax errors before running tests
                            fix_prompt = (
                                f"This Python code has syntax errors:\n"
                                f"```python\n{current_code}\n```\n"
                                f"Errors: {lint_output[:500]}\n"
                                f"Fix the syntax. Output only fixed code."
                            )
                            fix_resp = await self.router.generate(
                                messages=[{"role": "user", "content": fix_prompt}],
                                task_hint="think"
                            )
                            fixed = self._extract_code(fix_resp.get("text", ""))
                            if fixed:
                                current_code = fixed
                                await self.sandbox.run_command(
                                    session_id,
                                    f"cat > /home/ubuntu/workspace/{filename} "
                                    f"<< 'ARCHEOF'\n{current_code}\nARCHEOF"
                                )

                # Step 3: Run Test with coverage
                cov_result = await self.sandbox.run_command(
                    session_id,
                    f"cd /home/ubuntu/workspace && "
                    f"python -m pytest test_task.py -v --tb=short "
                    f"--cov=. --cov-report=term-missing 2>&1",
                    timeout=30
                )
                test_output = cov_result.get("output", "")

                # Section 4B: Auto-install missing modules
                if "ModuleNotFoundError" in test_output:
                    missing_match = re.search(
                        r"No module named '(\w+)'", test_output
                    )
                    if missing_match:
                        pkg = missing_match.group(1)
                        logger.info(f"TDD: auto-installing missing package: {pkg}")
                        await self.sandbox.run_command(
                            session_id,
                            f"pip install {pkg} --quiet 2>/dev/null",
                            timeout=30
                        )
                        continue  # Retry test after install
                break  # No missing module, exit pip retry loop

            # Check test results
            if cov_result.get("success") and "failed" not in test_output.lower():
                # Section 4A: Extract coverage percentage
                cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", test_output)
                coverage_pct = int(cov_match.group(1)) if cov_match else 0

                if coverage_pct < 60 and attempt < MAX_ITERATIONS - 1:
                    # Low coverage — ask for more tests
                    low_cov_prompt = (
                        f"Coverage is {coverage_pct}%. "
                        f"Add more tests to reach 80%+ coverage.\n"
                        f"Current tests:\n{test_code}\n"
                        f"Coverage report:\n{test_output[-500:]}\n"
                        f"Output ONLY the complete updated test file wrapped in ```python"
                    )
                    more_tests = await self.router.generate(
                        messages=[{"role": "user", "content": low_cov_prompt}],
                        task_hint="think"
                    )
                    new_test_code = self._extract_code(more_tests.get("text", ""))
                    if new_test_code:
                        test_code = new_test_code
                        await self.sandbox.run_command(
                            session_id,
                            f"cat > /home/ubuntu/workspace/test_task.py << 'ARCHEOF'\n"
                            f"{test_code}\nARCHEOF"
                        )
                        current_code = ""  # Force re-run tests
                        continue

                if websocket_send:
                    cov_info = f" (coverage: {coverage_pct}%)" if coverage_pct > 0 else ""
                    await websocket_send({
                        "type": "thought",
                        "content": f"🎉 TDD: Код прошел тесты (попытка {attempt+1})!{cov_info}",
                        "agent": "tdd_executor"
                    })
                return f"[TDD Success]\nIMPLEMENTATION:\n{current_code}\n\nTEST RUN:\n{test_output}"

            # Failed? Update prompt with error
            if websocket_send:
                await websocket_send({
                    "type": "thought",
                    "content": f"❌ TDD: Тесты упали. Исправление (попытка {attempt+1}/{MAX_ITERATIONS})...",
                    "agent": "tdd_executor"
                })

            impl_prompt = f"""
Task: {task}
Your previous code failed the tests.
TEST OUTPUT:
{test_output[-1500:]}

PREVIOUS CODE:
{current_code}

Fix the code. Output ONLY the python code for {filename} wrapped in ```python
"""
            current_code = ""  # Force regeneration on next iteration

        return f"[TDD Failed after {MAX_ITERATIONS} attempts]\nLast code:\n{current_code}"

    def _extract_code(self, text: str) -> str:
        matches = re.findall(r'```(?:python)?\n(.*?)\n```', text, re.DOTALL)
        return matches[0] if matches else text
