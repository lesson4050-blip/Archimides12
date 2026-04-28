"""Tests for OmegaCodeAct (test 1.8)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agent.omega_codeact import (
    OmegaCodeAct, TestResult, ExecutionState,
    MAX_ITERATIONS, PHASE_UNDERSTAND_ITERS,
    TASK_COMPLETE_SIGNAL, ROLLBACK_SIGNAL,
)


# ─── TestResult unit tests ───────────────────────────────────────

def test_test_result_defaults():
    r = TestResult()
    assert r.passed == 0 and r.failed == 0 and r.errors == 0
    assert r.total == 0
    assert r.success_rate == 0.0
    assert r.all_pass is True  # 0 failed, 0 errors = vacuously true


def test_test_result_computed_properties():
    r = TestResult(passed=8, failed=2, errors=1, failed_tests=["t1", "t2"])
    assert r.total == 11
    assert abs(r.success_rate - 8 / 11) < 1e-6
    assert r.all_pass is False


# ─── _parse_test_output ──────────────────────────────────────────

def test_parse_test_output_pytest_summary():
    router = MagicMock()
    oca = OmegaCodeAct(router)
    out = "===== 5 passed, 2 failed, 1 error in 3.14s ====="
    r = oca._parse_test_output(out)
    assert r.passed == 5
    assert r.failed == 2
    assert r.errors == 1


def test_parse_test_output_traceback():
    router = MagicMock()
    oca = OmegaCodeAct(router)
    out = 'FAILED tests/test_main.py::test_x\nFile "src/main.py", line 42\nAssertionError: expected True'
    r = oca._parse_test_output(out)
    assert r.failed_tests == ["tests/test_main.py::test_x"]
    assert r.relevant_file == "src/main.py"
    assert r.relevant_line == 42


def test_parse_test_output_empty():
    router = MagicMock()
    oca = OmegaCodeAct(router)
    r = oca._parse_test_output("")
    assert r.total == 0
    assert r.all_pass is True


# ─── ExecutionState ──────────────────────────────────────────────

def test_execution_state_defaults():
    s = ExecutionState(task="fix bug", session_id="s1")
    assert s.iteration == 0
    assert s.phase == "understand"
    assert s.modified_files == []
    assert s.best_test_score == 0.0


# ─── System prompt ───────────────────────────────────────────────

def test_build_system_prompt_phases():
    router = MagicMock()
    oca = OmegaCodeAct(router)
    state = ExecutionState(task="fix", session_id="s")
    for phase in ["understand", "localize", "implement", "verify"]:
        state.phase = phase
        prompt = oca._build_system_prompt(state)
        assert phase.upper() in prompt


def test_build_context_message():
    router = MagicMock()
    oca = OmegaCodeAct(router)
    state = ExecutionState(task="fix bug", session_id="s", iteration=5)
    state.modified_files = ["a.py"]
    tr = TestResult(passed=3, failed=1, failed_tests=["t1"])
    msg = oca._build_context_message(state, "output", tr)
    assert "fix bug" in msg
    assert "a.py" in msg
    assert "3 passed" in msg


def test_build_context_message_strategy_switch():
    router = MagicMock()
    oca = OmegaCodeAct(router)
    state = ExecutionState(task="fix", session_id="s", iteration=80)
    msg = oca._build_context_message(state)
    assert "STRATEGY SWITCH" in msg
