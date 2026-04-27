"""Tests for PersistentShellSession."""
import pytest
import asyncio


@pytest.mark.asyncio
async def test_persistent_shell_basic_command():
    """Basic command must return output."""
    from backend.tools.shell_tool import PersistentShellSession
    session = PersistentShellSession(session_id="test")
    
    result = await session.run("echo hello_archimedes")
    assert "hello_archimedes" in result
    
    await session.close()


@pytest.mark.asyncio
async def test_persistent_shell_state_preservation():
    """Shell must preserve state between calls (cd + pwd)."""
    from backend.tools.shell_tool import PersistentShellSession
    session = PersistentShellSession(session_id="test-state")
    
    await session.run("cd /tmp")
    result = await session.run("pwd")
    
    assert "/tmp" in result
    await session.close()


@pytest.mark.asyncio
async def test_persistent_shell_timeout():
    """Timeout must be handled gracefully without crashing."""
    from backend.tools.shell_tool import PersistentShellSession
    session = PersistentShellSession(session_id="test-timeout")
    
    result = await session.run("sleep 100", timeout=1)
    assert "TIMEOUT" in result or len(result) == 0
    
    await session.close()


@pytest.mark.asyncio
async def test_persistent_shell_multiple_sequential_commands():
    """Multiple commands must execute in sequence without corruption."""
    from backend.tools.shell_tool import PersistentShellSession
    session = PersistentShellSession(session_id="test-seq")
    
    r1 = await session.run("echo first")
    r2 = await session.run("echo second")
    r3 = await session.run("echo third")
    
    assert "first" in r1
    assert "second" in r2
    assert "third" in r3
    
    await session.close()
