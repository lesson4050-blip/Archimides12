"""Tests for self-improvement engine."""
import pytest
import os


@pytest.mark.asyncio
async def test_normalize_error_strips_line_numbers(temp_db):
    """Line numbers must be replaced with N placeholder."""
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "backend.agent.self_improvement.DB_PATH", temp_db
    ):
        from backend.agent.self_improvement import _normalize_error
        error = "File '/home/user/project/test.py', line 42, in my_function"
        normalized = _normalize_error(error)
        assert "42" not in normalized
        assert "N" in normalized


@pytest.mark.asyncio
async def test_normalize_error_strips_paths(temp_db):
    """File paths must be anonymized."""
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "backend.agent.self_improvement.DB_PATH", temp_db
    ):
        from backend.agent.self_improvement import _normalize_error
        error = "ImportError: No module named 'requests' in /usr/lib/python3.11/"
        normalized = _normalize_error(error)
        assert "/usr/lib/python3.11/" not in normalized


@pytest.mark.asyncio
async def test_normalize_error_strips_uuids(temp_db):
    """UUIDs must be replaced with UUID placeholder."""
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "backend.agent.self_improvement.DB_PATH", temp_db
    ):
        from backend.agent.self_improvement import _normalize_error
        error = "Session 550e8400-e29b-41d4-a716-446655440000 not found"
        normalized = _normalize_error(error)
        assert "550e8400" not in normalized
        assert "UUID" in normalized


@pytest.mark.asyncio
async def test_learn_and_retrieve_fix(temp_db):
    """Learned fix must be retrievable for the same error."""
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "backend.agent.self_improvement.DB_PATH", temp_db
    ):
        from backend.agent.self_improvement import learn_from_error, get_fix_hint
        
        error = "ModuleNotFoundError: No module named 'numpy'"
        fix = "pip install numpy --break-system-packages"
        
        await learn_from_error(error, fix, tool_name="shell", success=True)
        
        hint = await get_fix_hint(error, tool_name="shell")
        assert hint is not None
        assert "numpy" in hint or "pip" in hint


@pytest.mark.asyncio
async def test_check_tool_safety_blocks_rm_rf():
    """rm -rf / must be blocked by safety check."""
    from backend.agent.self_improvement import check_tool_safety
    is_safe, msg = await check_tool_safety(
        "shell", {"command": "rm -rf /"}
    )
    assert is_safe is False
    assert len(msg) > 0


@pytest.mark.asyncio
async def test_check_tool_safety_allows_normal_commands():
    """Normal commands must pass safety check."""
    from backend.agent.self_improvement import check_tool_safety
    is_safe, msg = await check_tool_safety(
        "shell", {"command": "ls -la /tmp"}
    )
    assert is_safe is True
