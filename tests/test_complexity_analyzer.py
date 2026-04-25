"""
Tests for LLM-based complexity analyzer in TaskProcessor.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def processor():
    from backend.agent.task_processor import TaskProcessor
    mock_router = MagicMock()
    mock_router.generate = AsyncMock()
    mock_cm = MagicMock()
    mock_registry = MagicMock()
    mock_registry.tools = {}
    return TaskProcessor(
        router=mock_router,
        context_manager=mock_cm,
        tool_registry=mock_registry,
        session_id="test"
    )


@pytest.mark.asyncio
async def test_valid_float_parsed(processor):
    processor.router.generate = AsyncMock(return_value={"text": "0.75"})
    score = await processor._analyze_complexity("Build a REST API")
    assert score == 0.75


@pytest.mark.asyncio
async def test_high_complexity(processor):
    processor.router.generate = AsyncMock(return_value={"text": "0.95"})
    score = await processor._analyze_complexity("Design distributed system")
    assert score == 0.95


@pytest.mark.asyncio
async def test_low_complexity(processor):
    processor.router.generate = AsyncMock(return_value={"text": "0.1"})
    score = await processor._analyze_complexity("Rename a variable")
    assert score == 0.1


@pytest.mark.asyncio
async def test_clamped_above_one(processor):
    processor.router.generate = AsyncMock(return_value={"text": "1.5"})
    score = await processor._analyze_complexity("Impossible task")
    assert score == 1.0


@pytest.mark.asyncio
async def test_clamped_below_zero(processor):
    processor.router.generate = AsyncMock(return_value={"text": "-0.3"})
    score = await processor._analyze_complexity("Trivial task")
    assert score == 0.0


@pytest.mark.asyncio
async def test_invalid_response_fallback(processor):
    processor.router.generate = AsyncMock(return_value={"text": "not a number"})
    score = await processor._analyze_complexity("Some task")
    assert score == 0.5


@pytest.mark.asyncio
async def test_empty_response_fallback(processor):
    processor.router.generate = AsyncMock(return_value={})
    score = await processor._analyze_complexity("Some task")
    assert score == 0.5


@pytest.mark.asyncio
async def test_exception_fallback(processor):
    processor.router.generate = AsyncMock(side_effect=Exception("LLM down"))
    score = await processor._analyze_complexity("Some task")
    assert score == 0.5
