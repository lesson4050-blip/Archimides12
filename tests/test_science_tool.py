"""Tests for ScienceTool."""
import pytest

@pytest.mark.asyncio
async def test_science_tool_thermal_conduction():
    from backend.tools.science_tool import ScienceTool
    tool = ScienceTool()
    # Q = k * A * dT / d
    result = await tool.execute(
        action="thermal_conduction",
        k=400, # Copper
        area=0.01,
        delta_t=50,
        thickness=0.05
    )
    assert result["success"] is True
    assert result["heat_transfer"] == 400 * 0.01 * 50 / 0.05

@pytest.mark.asyncio
async def test_science_tool_reynolds_number():
    from backend.tools.science_tool import ScienceTool
    tool = ScienceTool()
    # Re = (rho * v * L) / mu
    result = await tool.execute(
        action="reynolds_number",
        density=1000,
        velocity=2,
        length=0.1,
        viscosity=0.001
    )
    assert result["success"] is True
    assert result["reynolds_number"] == (1000 * 2 * 0.1) / 0.001

@pytest.mark.asyncio
async def test_science_tool_rc_circuit():
    from backend.tools.science_tool import ScienceTool
    tool = ScienceTool()
    # tau = R * C
    result = await tool.execute(
        action="rc_time_constant",
        resistance=1000,
        capacitance=0.001
    )
    assert result["success"] is True
    assert result["time_constant"] == 1.0
