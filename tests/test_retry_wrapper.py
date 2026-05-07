"""Tests for adaptive retry wrapper."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    from backend.models.retry_wrapper import with_retry, RetryConfig
    
    call_count = 0
    
    async def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("rate limit 429 try again")
        return {"text": "success"}
    
    config = RetryConfig(max_retries=3, base_delay=0.01)
    result = await with_retry(flaky_fn, config=config, operation_name="test")
    
    assert result["text"] == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_auth_errors():
    from backend.models.retry_wrapper import with_retry, RetryConfig
    
    call_count = 0
    
    async def auth_fail_fn():
        nonlocal call_count
        call_count += 1
        raise Exception("401 authentication failed invalid api key")
    
    config = RetryConfig(max_retries=3, base_delay=0.01)
    with pytest.raises(Exception, match="401"):
        await with_retry(auth_fail_fn, config=config, operation_name="test")
    
    assert call_count == 1  # No retries on auth error


@pytest.mark.asyncio
async def test_retry_uses_fallback_when_exhausted():
    from backend.models.retry_wrapper import with_retry, RetryConfig
    
    async def always_fails():
        raise Exception("503 service unavailable")
    
    async def fallback_fn():
        return {"text": "fallback response"}
    
    config = RetryConfig(max_retries=2, base_delay=0.01)
    result = await with_retry(
        always_fails, config=config,
        fallback=fallback_fn, operation_name="test"
    )
    
    assert result["text"] == "fallback response"


@pytest.mark.asyncio
async def test_git_tool_status():
    """Test GitTool status command (uses real git in repo)."""
    import os
    from backend.tools.git_tool import GitTool
    
    tool = GitTool()
    result = await tool.execute(
        action="status",
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    
    if not result["success"] and result.get("error") == "":
        pytest.skip("asyncio subprocess not supported on this event loop (Windows)")
        
    # Should succeed even if no changes
    assert result["success"] is True
    assert "output" in result
