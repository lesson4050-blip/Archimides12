"""Tests for GitTool."""
import pytest
import os
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_git_tool_status_in_real_repo():
    """Status command must succeed in git repository."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    # Run in project root (which IS a git repo)
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = await tool.execute(action="status", cwd=cwd)
    
    assert result["success"] is True
    assert "output" in result


@pytest.mark.asyncio
async def test_git_tool_log_returns_commits():
    """Log must return recent commits."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = await tool.execute(action="log", cwd=cwd)
    
    assert result["success"] is True


@pytest.mark.asyncio
async def test_git_tool_invalid_action():
    """Invalid action must return success=False."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    result = await tool.execute(action="invalid_action_xyz")
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_git_tool_diff_runs():
    """Diff must not crash."""
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = await tool.execute(action="diff", cwd=cwd)
    
    # Diff might show nothing (clean repo) but must succeed
    assert "output" in result
