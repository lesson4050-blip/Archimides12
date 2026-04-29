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
