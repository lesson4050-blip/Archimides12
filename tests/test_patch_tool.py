"""Tests for PatchTool."""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_patch_tool_preview():
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    
    with patch("builtins.open", MagicMock(read_data="def old(): pass")):
        with patch("os.path.exists", return_value=True):
            result = await tool.execute(
                action="preview",
                target_file="test.py",
                patch_content="--- test.py\n+++ test.py\n@@ -1 +1 @@\n-def old(): pass\n+def new(): pass"
            )
            assert result["success"] is True

@pytest.mark.asyncio
async def test_patch_tool_apply():
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    
    with patch("backend.tools.patch_tool.PatchTool._apply_patch", return_value=True):
        result = await tool.execute(
            action="apply",
            target_file="test.py",
            patch_content="--- test.py\n+++ test.py\n@@ -1 +1 @@\n-old\n+new"
        )
        assert result["success"] is True

@pytest.mark.asyncio
async def test_patch_tool_invalid_action():
    from backend.tools.patch_tool import PatchTool
    tool = PatchTool()
    result = await tool.execute(action="invalid_action", target_file="test.py", patch_content="")
    assert result["success"] is False
