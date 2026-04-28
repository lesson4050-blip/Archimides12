"""Tests for BioTool."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_bio_tool_invalid_action():
    """Unknown action must return success=False."""
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    result = await tool.execute(action="invalid_xyz")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_bio_tool_protein_no_identifier():
    """protein_info without identifier should fail."""
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    result = await tool.execute(action="protein_info")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_bio_tool_compound_no_identifier():
    """compound without identifier or smiles should fail."""
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    result = await tool.execute(action="compound")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_bio_tool_definition():
    """get_definition should return valid schema."""
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    defn = tool.get_definition()
    assert defn["function"]["name"] == "bio"
    params = defn["function"]["parameters"]["properties"]
    assert "action" in params
    assert set(params["action"]["enum"]) == {"protein_info", "alphafold", "compound"}
