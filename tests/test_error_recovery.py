"""Tests for ErrorRecovery v2 (test 1.10)."""
import pytest
from backend.agent.error_recovery import (
    ErrorRecovery, ErrorType, FailureRecord,
)


# ─── Error classification ────────────────────────────────────────

@pytest.mark.parametrize("error,expected", [
    ("SyntaxError: invalid syntax at line 10", ErrorType.SYNTAX),
    ("IndentationError: unexpected indent", ErrorType.SYNTAX),
    ("TimeoutError: deadline exceeded", ErrorType.TIMEOUT),
    ("PermissionError: access denied", ErrorType.PERMISSION),
    ("FileNotFoundError: No such file /tmp/x", ErrorType.NOT_FOUND),
    ("ModuleNotFoundError: No module named 'flask'", ErrorType.DEPENDENCY),
    ("ConnectionError: refused", ErrorType.NETWORK),
    ("Missing required field 'name'", ErrorType.TOOL_MISUSE),
    ("RuntimeError: unexpected failure", ErrorType.TOOL_MISUSE),
    ("something completely random xyzzy", ErrorType.UNKNOWN),
])
def test_classify_error(error, expected):
    assert ErrorRecovery.classify_error(error) == expected


# ─── Failure recording ───────────────────────────────────────────

def test_record_failure_increments_counter():
    er = ErrorRecovery()
    assert er.consecutive_failures == 0
    er.record_failure("shell", {"cmd": "ls"}, "permission denied")
    assert er.consecutive_failures == 1
    assert len(er.tool_failure_history) == 1
    assert er.tool_failure_history[0].error_type == ErrorType.PERMISSION


def test_record_success_resets_counter():
    er = ErrorRecovery()
    er.record_failure("shell", {"cmd": "ls"}, "error")
    er.record_failure("shell", {"cmd": "ls"}, "error")
    assert er.consecutive_failures == 2
    er.record_success()
    assert er.consecutive_failures == 0


# ─── Retry logic ─────────────────────────────────────────────────

def test_should_retry_within_limit():
    er = ErrorRecovery()
    er.record_failure("shell", {"cmd": "ls"}, "error")
    assert er.should_retry("shell", {"cmd": "ls"}) is True


def test_should_retry_exceeds_limit():
    er = ErrorRecovery()
    for _ in range(ErrorRecovery.MAX_RETRIES):
        er.record_failure("shell", {"cmd": "ls"}, "error")
    assert er.should_retry("shell", {"cmd": "ls"}) is False


def test_should_retry_kill_switch():
    er = ErrorRecovery()
    for i in range(ErrorRecovery.MAX_CONSECUTIVE_FAILURES):
        er.record_failure("shell", {"cmd": f"cmd{i}"}, "error")
    # Kill switch triggers — should NOT retry anything
    assert er.should_retry("shell", {"cmd": "new_cmd"}) is False


# ─── Recovery advice ─────────────────────────────────────────────

def test_get_recovery_advice_syntax():
    er = ErrorRecovery()
    advice = er.get_recovery_advice("file", "SyntaxError: invalid syntax")
    assert "SYNTAX ERROR" in advice
    assert "linter" in advice.lower() or "validate" in advice.lower()


def test_get_recovery_advice_unknown():
    er = ErrorRecovery()
    advice = er.get_recovery_advice("shell", "xyzzy weirdness")
    assert "UNKNOWN ERROR" in advice


def test_get_recovery_advice_repeated_failure():
    er = ErrorRecovery()
    er.record_failure("shell", {"cmd": "a"}, "SyntaxError: bad")
    er.record_failure("shell", {"cmd": "b"}, "SyntaxError: bad again")
    advice = er.get_recovery_advice("shell", "SyntaxError: still bad")
    assert "switching strategy" in advice.lower() or "failure #" in advice.lower()


# ─── Diagnostics ─────────────────────────────────────────────────

def test_get_failure_summary():
    er = ErrorRecovery()
    er.record_failure("shell", {"cmd": "ls"}, "timeout error")
    er.record_failure("file", {"path": "/x"}, "permission denied")
    summary = er.get_failure_summary()
    assert summary["total_failures"] == 2
    assert "timeout" in summary["failures_by_type"]
    assert "permission" in summary["failures_by_type"]
    assert "shell" in summary["failures_by_tool"]
    assert "file" in summary["failures_by_tool"]


# ─── Escalation ──────────────────────────────────────────────────

def test_should_escalate_kill_switch():
    er = ErrorRecovery()
    for i in range(ErrorRecovery.MAX_CONSECUTIVE_FAILURES):
        er.record_failure("shell", {"cmd": f"cmd{i}"}, "error")
    should, reason = er.should_escalate()
    assert should is True
    assert "Kill switch" in reason


def test_should_escalate_oscillation():
    er = ErrorRecovery()
    for _ in range(4):
        er.record_failure("shell", {"cmd": "x"}, "SyntaxError: bad")
        er.record_success()  # reset consecutive but keep history
    # Need 4 consecutive same-type without reset
    er2 = ErrorRecovery()
    for i in range(4):
        er2.record_failure("shell", {"cmd": f"c{i}"}, "SyntaxError: bad")
    should, reason = er2.should_escalate()
    # Either kill switch or oscillation should trigger
    assert should is True


def test_should_not_escalate_fresh():
    er = ErrorRecovery()
    er.record_failure("shell", {"cmd": "ls"}, "error")
    should, reason = er.should_escalate()
    assert should is False


# ─── Backoff ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_backoff_delay():
    """Backoff should complete without error."""
    er = ErrorRecovery()
    # Just verify it doesn't crash — actual sleep is short
    await er.backoff_delay(0)


# ─── Git checkpoints (no real git) ───────────────────────────────

@pytest.mark.asyncio
async def test_create_checkpoint_no_workspace():
    er = ErrorRecovery(workspace_dir=None)
    result = await er.create_checkpoint("session1")
    assert result is None


@pytest.mark.asyncio
async def test_rollback_no_checkpoint():
    er = ErrorRecovery()
    assert await er.rollback_to_checkpoint("unknown") is False
