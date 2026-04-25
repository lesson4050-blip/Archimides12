"""
Tests for PersistentShellSession — verifies state persistence and timeout handling.
"""
import asyncio
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Test: Session maintains state between calls ──

@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform == "win32", reason="Requires /bin/bash")
async def test_persistent_session_maintains_cwd():
    """cd /tmp in one call should be reflected in subsequent pwd call."""
    from backend.tools.shell_tool import PersistentShellSession

    session = PersistentShellSession(session_id="test-cwd")
    try:
        await session.run("cd /tmp")
        output = await session.run("pwd")
        assert "/tmp" in output, f"Expected /tmp in output, got: {output}"
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform == "win32", reason="Requires /bin/bash")
async def test_persistent_session_maintains_env_vars():
    """Environment variables set in one call should persist."""
    from backend.tools.shell_tool import PersistentShellSession

    session = PersistentShellSession(session_id="test-env")
    try:
        await session.run("export MY_TEST_VAR=hello123")
        output = await session.run("echo $MY_TEST_VAR")
        assert "hello123" in output, f"Expected 'hello123' in output, got: {output}"
    finally:
        await session.close()


# ── Test: Timeout handling ──

@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform == "win32", reason="Requires /bin/bash")
async def test_persistent_session_timeout():
    """Commands exceeding timeout should return timeout message."""
    from backend.tools.shell_tool import PersistentShellSession

    session = PersistentShellSession(session_id="test-timeout")
    try:
        output = await session.run("sleep 10", timeout=1)
        assert "TIMEOUT" in output, f"Expected TIMEOUT in output, got: {output}"
    finally:
        await session.close()


# ── Test: Session registry ──

def test_session_registry_creates_and_reuses():
    """get_persistent_session should return the same object for the same ID."""
    from backend.tools.shell_tool import get_persistent_session, _persistent_sessions

    # Clean up any existing test sessions
    _persistent_sessions.pop("test-registry", None)

    s1 = get_persistent_session("test-registry")
    s2 = get_persistent_session("test-registry")
    assert s1 is s2, "Expected same session object for same session_id"

    # Cleanup
    _persistent_sessions.pop("test-registry", None)


# ── Test: ShellTool falls back gracefully ──

@pytest.mark.asyncio
async def test_shell_tool_returns_error_without_command():
    """ShellTool.execute should return error when command is missing."""
    from backend.tools.shell_tool import ShellTool

    mock_executor = MagicMock()
    tool = ShellTool(executor=mock_executor)
    result = await tool.execute(session_id="test", action="exec", command=None)
    assert result["success"] is False
    assert "required" in result["error"].lower()
