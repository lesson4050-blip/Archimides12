"""Tests for EvalPipeline."""
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_run_task_success():
    from backend.benchmarks.eval_pipeline import EvalPipeline, EvalTask

    mock_router = AsyncMock()
    mock_router.generate = AsyncMock(return_value={
        "text": "def check_palindrome(s): return s == s[::-1]",
        "tool_call": None,
        "tokens_used": 50
    })

    pipeline = EvalPipeline(mock_router)
    task = EvalTask(
        id="test_1", category="code",
        prompt="Write a palindrome checker",
        expected_contains=["def ", "return"]
    )
    result = await pipeline.run_task(task, "default")
    assert result.success is True
    assert result.task_id == "test_1"
