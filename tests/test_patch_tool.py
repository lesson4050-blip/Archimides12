"""Tests for PatchTool."""
import os
import pytest


@pytest.mark.asyncio
async def test_patch_tool_diff():
    """Diff action should produce a diff between two strings."""
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    result = await tool.execute(
        action="diff",
        original="def old(): pass\n",
        modified="def new(): pass\n"
    )
    if os.name == "nt":
        # diff command may not exist on Windows — accept either outcome
        assert isinstance(result["success"], bool)
    else:
        assert result["success"] is True


@pytest.mark.asyncio
async def test_patch_tool_diff_missing_params():
    """Diff without original/modified should fail gracefully."""
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    result = await tool.execute(action="diff")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_patch_tool_invalid_action():
    """Unknown action must return success=False."""
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    result = await tool.execute(action="invalid_action")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_patch_tool_apply_missing_patch():
    """Apply without patch content should fail gracefully."""
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    result = await tool.execute(action="apply")
    assert result["success"] is False
