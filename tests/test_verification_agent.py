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
