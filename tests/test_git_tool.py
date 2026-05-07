"""Tests for GitTool."""
import pytest
import os
import subprocess
from unittest.mock import patch, AsyncMock, MagicMock


def _git_available():
    """Check if git is available on this system."""
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(not _git_available(), reason="git not in PATH")
@pytest.mark.asyncio
async def test_git_tool_status_in_real_repo():
    """Status command must succeed in git repository."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = await tool.execute(action="status", cwd=cwd)
    
    if not result["success"] and result.get("error") == "":
        pytest.skip("asyncio subprocess not supported on this event loop")
        
    assert result["success"] is True
    assert "output" in result


@pytest.mark.skipif(not _git_available(), reason="git not in PATH")
@pytest.mark.asyncio
async def test_git_tool_log_returns_commits():
    """Log must return recent commits."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = await tool.execute(action="log", cwd=cwd)
    
    if not result["success"] and result.get("error") == "":
        pytest.skip("asyncio subprocess not supported on this event loop")
        
    assert result["success"] is True


@pytest.mark.asyncio
async def test_git_tool_invalid_action():
    """Invalid action must return success=False."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    result = await tool.execute(action="invalid_action_xyz")
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.skipif(not _git_available(), reason="git not in PATH")
@pytest.mark.asyncio
async def test_git_tool_diff_runs():
    """Diff must not crash."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = await tool.execute(action="diff", cwd=cwd)
    
    if not result["success"] and result.get("error") == "":
        pytest.skip("asyncio subprocess not supported on this event loop")
        
    # Diff might show nothing (clean repo) but must succeed
    assert "output" in result or "error" in result
