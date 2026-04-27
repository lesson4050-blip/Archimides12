"""Tests for FinanceTool."""
import pytest

@pytest.mark.asyncio
async def test_finance_tool_compound_interest():
    from backend.tools.finance_tool import FinanceTool
    tool = FinanceTool()
    result = await tool.execute(
        action="compound_interest",
        principal=1000,
        rate=0.05,
        time=10,
        times_compounded=1
    )
    assert result["success"] is True
    # A = P(1 + r/n)^(nt) -> 1000 * (1.05)^10 ≈ 1628.89
    assert abs(result["final_amount"] - 1628.89) < 0.05

@pytest.mark.asyncio
async def test_finance_tool_rsi_calculation_bounds():
    from backend.tools.finance_tool import FinanceTool
    tool = FinanceTool()
    result = await tool.execute(
        action="rsi",
        prices=[10, 11, 12, 11, 13, 14, 15, 14, 16, 17, 18, 17, 19, 20]
    )
    assert result["success"] is True
    assert 0 <= result["rsi"] <= 100

@pytest.mark.asyncio
async def test_finance_tool_invalid_action():
    from backend.tools.finance_tool import FinanceTool
    tool = FinanceTool()
    result = await tool.execute(action="invalid")
    assert result["success"] is False
