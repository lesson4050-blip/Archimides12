"""Tests for FinanceTool."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_finance_tool_invalid_action():
    """Unknown action must return success=False."""
    from backend.tools.finance_tool import FinanceTool
    tool = FinanceTool()
    result = await tool.execute(action="invalid_nonexistent_action_xyz")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_finance_tool_crypto_price_mocked():
    """Test crypto price action with mocked HTTP."""
    from backend.tools.finance_tool import FinanceTool
    tool = FinanceTool()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{
        "name": "Bitcoin", "symbol": "btc", "current_price": 65000,
        "price_change_percentage_24h": 2.5, "market_cap": 1200000000000,
        "total_volume": 30000000000, "high_24h": 66000, "low_24h": 64000,
        "ath": 73000, "ath_change_percentage": -10, "market_cap_rank": 1,
        "price_change_percentage_1h_in_currency": 0.3,
        "price_change_percentage_7d_in_currency": 5.1
    }]
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_response))
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        # Real action name from finance_tool.py is "crypto"
        result = await tool.execute(action="crypto", symbol="bitcoin")
        assert result["success"] is True


@pytest.mark.asyncio
async def test_finance_tool_fear_greed_mocked():
    """Test fear & greed action with mocked HTTP."""
    from backend.tools.finance_tool import FinanceTool
    tool = FinanceTool()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{
            "value": "25", "value_classification": "Extreme Fear",
            "timestamp": "1714300800"
        }]
    }
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_response))
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await tool.execute(action="fear_greed")
        assert result["success"] is True
