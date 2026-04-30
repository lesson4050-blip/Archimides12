"""Tests for VerificationAgent."""
import pytest
from backend.agent.orchestration.agents.verification_agent import (
    classify_change_type, ChangeType, VerificationReport,
    VerificationCheck, VerificationStatus
)


def test_classify_backend_py():
    ct = classify_change_type(["backend/agent/core.py"])
    assert ct == ChangeType.BACKEND


def test_classify_frontend_tsx():
    ct = classify_change_type(["frontend/components/Chat.tsx"])
    assert ct == ChangeType.FRONTEND


def test_classify_test_files():
    ct = classify_change_type(["tests/test_something.py"])
    assert ct == ChangeType.TEST


def test_report_passed_when_no_failures():
    report = VerificationReport(change_type=ChangeType.BACKEND)
    report.add_check(VerificationCheck(name="pytest", status=VerificationStatus.PASSED))
    assert report.passed is True


def test_report_failed_when_has_failures():
    report = VerificationReport(change_type=ChangeType.BACKEND)
    report.add_check(VerificationCheck(name="pytest", status=VerificationStatus.FAILED))
    assert report.passed is False


class TestAdversarialMode:
    def test_adversarial_checks_list(self):
        from backend.agent.orchestration.agents.verification_agent import VerificationAgent
        assert len(VerificationAgent.ADVERSARIAL_CHECKS) >= 5
        assert "empty_input" in VerificationAgent.ADVERSARIAL_CHECKS

    @pytest.mark.asyncio
    async def test_adversarial_skipped_without_executor(self):
        from unittest.mock import AsyncMock
        from backend.agent.orchestration.agents.verification_agent import VerificationAgent
        mock_router = AsyncMock()
        agent = VerificationAgent(mock_router)
        report = await agent.adversarial_verify(
            changed_files=["backend/test.py"],
            task="Fix bug",
            tool_executor=None
        )
        assert any(c.status.value == "skipped" for c in report.checks)
