"""Tests for SWE-bench adapter."""
from backend.benchmarks.swe_bench_adapter import SWEBenchTask, SWEBenchResult


class TestSWEBenchTask:
    def test_task_creation(self):
        task = SWEBenchTask(
            instance_id="django__django-11099",
            repo="django/django",
            base_commit="abc123",
            problem_statement="Fix the bug in QuerySet.filter()"
        )
        assert task.instance_id == "django__django-11099"
        assert task.hints_text == ""

    def test_result_default_not_resolved(self):
        result = SWEBenchResult(instance_id="test-1", resolved=False)
        assert not result.resolved
        assert result.agent_patch == ""
        assert result.error == ""

    def test_result_resolved(self):
        result = SWEBenchResult(
            instance_id="test-2", resolved=True,
            agent_patch="diff --git a/fix.py b/fix.py\n+fix code"
        )
        assert result.resolved
        assert "fix" in result.agent_patch
