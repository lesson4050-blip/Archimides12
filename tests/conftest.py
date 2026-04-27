"""
Shared pytest fixtures for Archimedes test suite.
All fixtures use mocking — no real API calls in unit tests.
"""
import asyncio
import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


@pytest.fixture
def mock_router():
    """Mock ModelRouter that returns predictable responses."""
    router = AsyncMock()
    router.generate = AsyncMock(return_value={
        "text": "Mock response",
        "tool_call": None,
        "model_used": "mock-model"
    })
    router.generate_stream = AsyncMock(return_value={
        "text": "Mock stream response",
        "tool_call": None,
        "model_used": "mock-model"
    })
    return router


@pytest.fixture
def mock_sandbox():
    """Mock sandbox executor."""
    sandbox = AsyncMock()
    sandbox.execute_code = AsyncMock(return_value={
        "success": True,
        "output": "Mock output",
        "error": ""
    })
    sandbox.execute_command = AsyncMock(return_value={
        "success": True,
        "stdout": "mock stdout",
        "stderr": "",
        "returncode": 0
    })
    return sandbox


@pytest.fixture
def temp_db(tmp_path):
    """In-memory SQLite database for tests."""
    db_path = tmp_path / "test.db"
    return str(db_path)


@pytest.fixture
def mock_tool_registry():
    """Mock tool registry with basic tools."""
    registry = MagicMock()
    registry.tools = {}
    registry.register = lambda name, fn: registry.tools.update({name: fn})
    return registry


@pytest.fixture
async def test_agent(mock_router, mock_tool_registry, tmp_path):
    """Minimal initialized agent for testing."""
    with patch("backend.models.model_router.ModelRouter", return_value=mock_router):
        with patch("backend.agent.tool_initializer.ToolInitializer") as mock_init:
            mock_init.return_value.initialize_all = AsyncMock()
            from backend.agent.core import ArchimedesCosmoAgent
            agent = ArchimedesCosmoAgent(
                name="TestAgent",
                session_id="test-session"
            )
            agent.router = mock_router
            return agent
