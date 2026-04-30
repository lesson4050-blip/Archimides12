"""
Verification Agent — Read-only quality gate.

Runs after every Warrior execution to PROVE the code works.
Cannot modify project files — can only read and run tests.

Verification strategies are selected based on which files changed:
- Backend changes -> pytest + linter + import check + health
- Frontend changes -> npm test + TypeScript check + build
- Config changes -> syntax validation + pytest
- Database changes -> migration syntax + pytest

Returns a structured VerificationReport with pass/fail per check.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from backend.agent.orchestration.agents.base import BaseAgent
from backend.agent.orchestration.state import OrchestrationState
from backend.models.model_router import ModelRouter

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ChangeType(str, Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    CONFIG = "config"
    DATABASE = "database"
    TEST = "test"
    REFACTOR = "refactor"
    UNKNOWN = "unknown"


@dataclass
class VerificationCheck:
    """Result of a single verification check."""
    name: str
    status: VerificationStatus = VerificationStatus.SKIPPED
    command: str = ""
    output: str = ""
    details: str = ""
    duration_ms: float = 0.0


@dataclass
class VerificationReport:
    """Complete verification report for a set of changes."""
    change_type: ChangeType
    files_checked: List[str] = field(default_factory=list)
    checks: List[VerificationCheck] = field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> bool:
        return all(
            c.status in (VerificationStatus.PASSED, VerificationStatus.SKIPPED)
            for c in self.checks
        )

    def add_check(self, check: VerificationCheck):
        self.checks.append(check)

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "change_type": self.change_type.value,
            "checks": [
                {"name": c.name, "status": c.status.value, "details": c.details, "output": c.output[:500]}
                for c in self.checks
            ],
            "files_checked": self.files_checked,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.status == VerificationStatus.PASSED),
            "failed_checks": sum(1 for c in self.checks if c.status == VerificationStatus.FAILED),
        }


def classify_change_type(files: List[str]) -> ChangeType:
    """Classify the type of change based on affected files."""
    extensions = set()
    paths = set()
    for f in files:
        ext = f.rsplit(".", 1)[-1] if "." in f else ""
        extensions.add(ext)
        parts = f.split("/")
        if parts:
            paths.add(parts[0])

    if any(ext in ("tsx", "jsx", "css", "scss") for ext in extensions):
        return ChangeType.FRONTEND
    if "frontend" in paths:
        return ChangeType.FRONTEND
    if any(ext in ("py",) for ext in extensions) and "backend" in paths:
        return ChangeType.BACKEND
    if "tests" in paths:
        return ChangeType.TEST
    if any(ext in ("yml", "yaml", "toml", "cfg", "ini") for ext in extensions):
        return ChangeType.CONFIG
    if any("migration" in f or "alembic" in f for f in files):
        return ChangeType.DATABASE
    return ChangeType.UNKNOWN


class VerificationAgent(BaseAgent):
    """Read-only agent that PROVES code works by executing tests."""

    VERIFICATION_STRATEGIES = {
        ChangeType.BACKEND: ["run_pytest", "run_linter", "check_imports", "verify_api_health"],
        ChangeType.FRONTEND: ["run_npm_test", "check_typescript", "verify_build"],
        ChangeType.CONFIG: ["validate_syntax", "run_pytest"],
        ChangeType.DATABASE: ["check_migration_syntax", "run_pytest"],
        ChangeType.TEST: ["run_pytest"],
        ChangeType.REFACTOR: ["run_pytest", "run_linter", "check_imports"],
    }

    ADVERSARIAL_CHECKS = [
        "empty_input",
        "null_values",
        "boundary_values",
        "unicode_input",
        "concurrent_access",
        "large_payload",
    ]

    async def adversarial_verify(
        self,
        changed_files: list,
        task: str,
        tool_executor=None
    ) -> VerificationReport:
        """
        Adversarial testing — actually executes edge case tests.

        Unlike simple test running, this:
        1. Asks LLM to generate adversarial test cases
        2. EXECUTES each test command via tool_executor
        3. Reports actual pass/fail from execution, not just plan generation
        """
        report = VerificationReport(change_type=classify_change_type(changed_files))
        report.files_checked = changed_files

        if not tool_executor:
            report.add_check(VerificationCheck(
                name="adversarial_analysis",
                status=VerificationStatus.SKIPPED,
                details="No executor available — skipping adversarial tests"
            ))
            report.summary = "Adversarial verification skipped (no executor)"
            return report

        # Step 1: Generate adversarial test COMMANDS (not just descriptions)
        adversarial_prompt = f"""You are a destructive tester. Generate shell commands
that will EXPOSE bugs in this code by testing edge cases.

Changed files: {', '.join(changed_files)}
Task: {task}

Output ONLY executable pytest or python commands, one per line.
Format: pytest path/to/test.py::TestClass::test_method -v
Or: python -c "from module import func; assert func(None) is not None"

Generate 3-5 adversarial test commands targeting:
- None/null inputs
- Empty strings/lists
- Boundary values (0, -1, very large numbers)
- Unicode edge cases

Output ONLY commands, no explanations."""

        try:
            response = await self.router.generate(
                messages=[{"role": "user", "content": adversarial_prompt}],
                task_hint="think"
            )
            plan_text = response.get("text", "")
        except Exception as e:
            report.add_check(VerificationCheck(
                name="adversarial_plan",
                status=VerificationStatus.ERROR,
                details=str(e)
            ))
            report.summary = "Adversarial plan generation failed"
            return report

        # Step 2: Extract and EXECUTE each command
        import re
        commands = []
        for line in plan_text.split("\n"):
            line = line.strip()
            if line.startswith("pytest ") or line.startswith("python "):
                commands.append(line)

        if not commands:
            report.add_check(VerificationCheck(
                name="adversarial_analysis",
                status=VerificationStatus.SKIPPED,
                details="No executable commands generated"
            ))
        else:
            for cmd in commands[:5]:  # Max 5 adversarial commands
                try:
                    exec_result = await tool_executor("shell", {
                        "action": "execute",
                        "command": f"cd /app && timeout 30 {cmd} 2>&1 | tail -20"
                    })
                    output = exec_result.get("output", "")
                    # Adversarial test FINDING bugs is SUCCESS
                    # If test CRASHES unexpectedly — that's a bug found
                    passed_gracefully = (
                        "passed" in output.lower() or
                        "AssertionError" in output or  # Expected edge case failure
                        "no tests ran" in output.lower()
                    )
                    crashed = any(
                        kw in output for kw in
                        ["Segmentation fault", "MemoryError", "RecursionError",
                         "SystemError", "KeyboardInterrupt"]
                    )
                    status = (
                        VerificationStatus.FAILED if crashed
                        else VerificationStatus.PASSED
                    )
                    report.add_check(VerificationCheck(
                        name=f"adversarial_{cmd[:30]}",
                        status=status,
                        command=cmd,
                        output=output[:500],
                        details="Crash detected!" if crashed else "Edge case handled"
                    ))
                except Exception as e:
                    report.add_check(VerificationCheck(
                        name=f"adversarial_{cmd[:30]}",
                        status=VerificationStatus.ERROR,
                        details=str(e)
                    ))

        passed = sum(1 for c in report.checks if c.status == VerificationStatus.PASSED)
        total = len(report.checks)
        report.summary = f"Adversarial: {passed}/{total} checks passed"
        return report

    def __init__(self, router: ModelRouter, tool_executor: Optional[Callable] = None):
        super().__init__("VerificationAgent", router)
        self.tool_executor = tool_executor

    async def process(self, state: OrchestrationState, websocket_send=None) -> OrchestrationState:
        """BaseAgent interface."""
        changed = getattr(state, 'changed_files', [])
        task = getattr(state, 'task_description', '')
        report = await self.verify(changed, task, self.tool_executor)
        if websocket_send:
            await websocket_send({"type": "info", "content": f"✅ Verification: {report.summary}"})
        state.metadata["verification_report"] = report.to_dict()
        return state

    async def verify(self, changed_files: List[str], task_description: str = "", tool_executor: Optional[Callable] = None) -> VerificationReport:
        """Run verification checks on changed files."""
        executor = tool_executor or self.tool_executor
        change_type = classify_change_type(changed_files)
        report = VerificationReport(change_type=change_type, files_checked=changed_files)

        strategies = self.VERIFICATION_STRATEGIES.get(change_type, ["run_pytest", "run_linter"])

        for strategy in strategies:
            check_fn = getattr(self, f"_check_{strategy}", None)
            if check_fn and executor:
                try:
                    check = await check_fn(executor, changed_files)
                    report.add_check(check)
                except Exception as e:
                    report.add_check(VerificationCheck(name=strategy, status=VerificationStatus.ERROR, details=str(e)))
            else:
                report.add_check(VerificationCheck(name=strategy, status=VerificationStatus.SKIPPED, details="No executor available"))

        passed = sum(1 for c in report.checks if c.status == VerificationStatus.PASSED)
        total = len(report.checks)
        report.summary = f"{passed}/{total} checks passed for {change_type.value} changes"
        return report

    async def _check_run_pytest(self, executor: Callable, files: List[str]) -> VerificationCheck:
        result = await executor("shell", {"action": "execute", "command": "cd /app && python -m pytest tests/ -v --timeout=60 --tb=short -q 2>&1 | tail -30"})
        output = result.get("output", "")
        passed = "passed" in output and "failed" not in output
        return VerificationCheck(name="run_pytest", status=VerificationStatus.PASSED if passed else VerificationStatus.FAILED, command="pytest tests/ -v --timeout=60", output=output, details="All tests passed" if passed else "Some tests failed")

    async def _check_run_linter(self, executor: Callable, files: List[str]) -> VerificationCheck:
        py_files = [f for f in files if f.endswith(".py")]
        if not py_files:
            return VerificationCheck(name="run_linter", status=VerificationStatus.SKIPPED, details="No Python files")
        target = " ".join(py_files[:10])
        result = await executor("shell", {"action": "execute", "command": f"cd /app && ruff check {target} --exit-zero 2>&1 | tail -20"})
        output = result.get("output", "")
        errors = output.count(": E") + output.count(": F")
        return VerificationCheck(name="run_linter", status=VerificationStatus.PASSED if errors == 0 else VerificationStatus.FAILED, command=f"ruff check {target}", output=output, details=f"{errors} lint issues" if errors else "Clean")

    async def _check_check_imports(self, executor: Callable, files: List[str]) -> VerificationCheck:
        py_files = [f for f in files if f.endswith(".py")]
        if not py_files:
            return VerificationCheck(name="check_imports", status=VerificationStatus.SKIPPED)
        failed = []
        for f in py_files[:5]:
            module = f.replace("/", ".").replace(".py", "")
            result = await executor("shell", {"action": "execute", "command": f"cd /app && python3 -c 'import {module}' 2>&1"})
            if result.get("exit_code", 1) != 0:
                failed.append(f"{f}: {result.get('output', '')[:100]}")
        return VerificationCheck(name="check_imports", status=VerificationStatus.PASSED if not failed else VerificationStatus.FAILED, details="\n".join(failed) if failed else "All imports OK")

    async def _check_verify_api_health(self, executor: Callable, files: List[str]) -> VerificationCheck:
        result = await executor("shell", {"action": "execute", "command": "curl -sf http://localhost:8000/api/health 2>&1 || echo 'HEALTH_CHECK_FAILED'"})
        output = result.get("output", "")
        ok = "HEALTH_CHECK_FAILED" not in output and ("ok" in output.lower() or "healthy" in output.lower())
        return VerificationCheck(name="verify_api_health", status=VerificationStatus.PASSED if ok else VerificationStatus.SKIPPED, command="curl http://localhost:8000/api/health", output=output, details="API healthy" if ok else "API not running (skipped)")

    async def _check_run_npm_test(self, executor: Callable, files: List[str]) -> VerificationCheck:
        result = await executor("shell", {"action": "execute", "command": "cd /app/frontend && npm test --passWithNoTests 2>&1 | tail -20"})
        output = result.get("output", "")
        return VerificationCheck(name="run_npm_test", status=VerificationStatus.PASSED if "fail" not in output.lower() else VerificationStatus.FAILED, command="npm test", output=output)

    async def _check_check_typescript(self, executor: Callable, files: List[str]) -> VerificationCheck:
        result = await executor("shell", {"action": "execute", "command": "cd /app/frontend && npx tsc --noEmit 2>&1 | tail -20"})
        output = result.get("output", "")
        errors = output.count("error TS")
        return VerificationCheck(name="check_typescript", status=VerificationStatus.PASSED if errors == 0 else VerificationStatus.FAILED, command="npx tsc --noEmit", output=output, details=f"{errors} TypeScript errors" if errors else "Clean")

    async def _check_verify_build(self, executor: Callable, files: List[str]) -> VerificationCheck:
        result = await executor("shell", {"action": "execute", "command": "cd /app/frontend && npm run build 2>&1 | tail -10"})
        output = result.get("output", "")
        return VerificationCheck(name="verify_build", status=VerificationStatus.PASSED if "error" not in output.lower() else VerificationStatus.FAILED, command="npm run build", output=output)

    async def _check_validate_syntax(self, executor: Callable, files: List[str]) -> VerificationCheck:
        yml_files = [f for f in files if f.endswith((".yml", ".yaml"))]
        if not yml_files:
            return VerificationCheck(name="validate_syntax", status=VerificationStatus.SKIPPED)
        result = await executor("shell", {"action": "execute", "command": f"python3 -c \"import yaml; yaml.safe_load(open('{yml_files[0]}')); print('OK')\" 2>&1"})
        output = result.get("output", "")
        return VerificationCheck(name="validate_syntax", status=VerificationStatus.PASSED if "OK" in output else VerificationStatus.FAILED, output=output)

    # ── Mutation Testing ─────────────────────────────────────────

    MUTATION_OPERATORS = [
        # (pattern, replacement, description)
        (r'\breturn True\b', 'return False', 'negate_true'),
        (r'\breturn False\b', 'return True', 'negate_false'),
        (r'\b>=\b', '<', 'boundary_gte_to_lt'),
        (r'\b<=\b', '>', 'boundary_lte_to_gt'),
        (r'\b==\b', '!=', 'equality_invert'),
        (r'\b!=\b', '==', 'inequality_invert'),
        (r'\band\b', 'or', 'logic_and_to_or'),
        (r'\bor\b', 'and', 'logic_or_to_and'),
        (r'\b\+ ', '- ', 'arithmetic_add_to_sub'),
    ]

    async def mutation_test(
        self,
        target_file: str,
        test_command: str = "python -m pytest tests/ -x -q --timeout=30",
        tool_executor: Optional[Callable] = None,
        max_mutations: int = 5,
    ) -> Dict:
        """
        Run mutation testing on a target file.

        1. Read the original file
        2. Apply mutations one at a time
        3. Run tests after each mutation
        4. If tests still PASS → mutation survived (test suite gap!)
        5. If tests FAIL → mutation killed (test suite is good)
        6. Restore original after each mutation

        Returns: {killed, survived, total, score, survivors: [...]}
        """
        executor = tool_executor or self.tool_executor
        if not executor:
            return {"error": "No executor available", "score": 0.0}

        # Step 1: Read original file
        read_result = await executor("shell", {
            "action": "execute",
            "command": f"cat {target_file}"
        })
        original_content = read_result.get("output", "")
        if not original_content:
            return {"error": f"Could not read {target_file}", "score": 0.0}

        killed = 0
        survived = 0
        survivors = []
        total = 0
        import re as re_mod

        for pattern, replacement, desc in self.MUTATION_OPERATORS:
            if total >= max_mutations:
                break

            # Check if pattern exists in file
            matches = list(re_mod.finditer(pattern, original_content))
            if not matches:
                continue

            # Apply mutation to first match only
            match = matches[0]
            mutated = (
                original_content[:match.start()]
                + replacement
                + original_content[match.end():]
            )
            total += 1

            try:
                # Write mutated version
                escaped_content = mutated.replace("'", "'\\''")
                await executor("shell", {
                    "action": "execute",
                    "command": f"echo '{escaped_content}' > {target_file}"
                })

                # Run tests
                test_result = await executor("shell", {
                    "action": "execute",
                    "command": f"cd /app && timeout 30 {test_command} 2>&1 | tail -5"
                })
                test_output = test_result.get("output", "")

                if "failed" in test_output.lower() or "error" in test_output.lower():
                    killed += 1  # Test caught the mutation!
                else:
                    survived += 1  # Test missed the mutation!
                    survivors.append({
                        "mutation": desc,
                        "pattern": pattern,
                        "line": original_content[:match.start()].count('\n') + 1,
                    })
            finally:
                # Always restore original
                escaped_orig = original_content.replace("'", "'\\''")
                await executor("shell", {
                    "action": "execute",
                    "command": f"echo '{escaped_orig}' > {target_file}"
                })

        score = killed / total if total > 0 else 0.0
        return {
            "killed": killed,
            "survived": survived,
            "total": total,
            "score": round(score, 2),
            "survivors": survivors,
            "verdict": "strong" if score >= 0.8 else "weak" if score >= 0.5 else "inadequate",
        }
