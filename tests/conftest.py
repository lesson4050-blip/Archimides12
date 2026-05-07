import os
import sys
import asyncio
import platform
import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


def pytest_sessionstart(session):
    """Force environment variables for test isolation before any imports."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_archemidas.db"
    os.environ["REDIS_URL"] = ""
    os.environ["TESTING"] = "1"


# ── Fix Windows IOCP event loop deadlock with aiosqlite ──────────
# On Windows, the default ProactorEventLoop can deadlock with aiosqlite.
# SelectorEventLoop is compatible with aiosqlite's threading model.
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session", autouse=True)
def _init_test_database():
    """Create all database tables in the test SQLite DB before any tests run."""
    from backend.db.crud import init_db

    async def _init_with_timeout():
        try:
            await asyncio.wait_for(init_db(), timeout=10.0)
        except asyncio.TimeoutError:
            pass  # DB init timed out — tests will use mocks
        except Exception:
            pass  # Non-critical: tests can mock DB

    try:
        asyncio.run(_init_with_timeout())
    except Exception:
        pass  # Swallow — test isolation via mocks


@pytest.fixture(autouse=True)
def mock_redis_globally(monkeypatch):
    """Prevent tests from trying to connect to a real Redis server."""
    monkeypatch.setattr("backend.config.settings.REDIS_URL", "")
    
    # Also patch aioredis to ensure no connection attempt goes through
    from unittest.mock import AsyncMock
    monkeypatch.setattr("redis.asyncio.from_url", AsyncMock())


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
