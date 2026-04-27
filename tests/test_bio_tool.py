"""Tests for BioTool."""
import pytest

@pytest.mark.asyncio
async def test_bio_tool_gc_content():
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    result = await tool.execute(action="gc_content", sequence="GCATGCAT")
    assert result["success"] is True
    assert result["gc_percent"] == 50.0

@pytest.mark.asyncio
async def test_bio_tool_complement_strand():
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    result = await tool.execute(action="complement", sequence="ACGT")
    assert result["success"] is True
    assert result["complement"] == "TGCA"

@pytest.mark.asyncio
async def test_bio_tool_dna_translate():
    from backend.tools.bio_tool import BioTool
    tool = BioTool()
    result = await tool.execute(action="translate", sequence="ATGTAA")
    assert result["success"] is True
    # ATG -> M (Start), TAA -> * (Stop)
    assert result["protein"] == "M*"
