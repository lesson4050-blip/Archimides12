"""Tests for CADTool."""
import pytest
import os

@pytest.mark.asyncio
async def test_cad_tool_openscad_generation(tmp_path):
    from backend.tools.cad_tool import CADTool
    tool = CADTool()
    
    out_file = tmp_path / "test.scad"
    result = await tool.execute(
        action="generate_cube",
        size=[10, 20, 30],
        output_path=str(out_file)
    )
    
    assert result["success"] is True
    assert os.path.exists(out_file)
    content = out_file.read_text()
    assert "cube([10, 20, 30])" in content

@pytest.mark.asyncio
async def test_cad_tool_threejs_generation(tmp_path):
    from backend.tools.cad_tool import CADTool
    tool = CADTool()
    
    out_file = tmp_path / "test.html"
    result = await tool.execute(
        action="generate_threejs",
        geometry="sphere",
        radius=5,
        output_path=str(out_file)
    )
    
    assert result["success"] is True
    assert os.path.exists(out_file)
    content = out_file.read_text()
    assert "three.js" in content.lower() or "three" in content.lower()
    assert "SphereGeometry" in content

@pytest.mark.asyncio
async def test_cad_tool_invalid_action():
    from backend.tools.cad_tool import CADTool
    tool = CADTool()
    
    result = await tool.execute(action="invalid_action_xyz")
    assert result["success"] is False
