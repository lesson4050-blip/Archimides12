"""
Financial Market Data Tool — CoinGecko crypto prices and
Fear & Greed Index. API-only, zero formulas.

The LLM can compute compound interest / Black-Scholes / DCF
natively — wrapping textbook math adds zero value. What *does*
add value is live market data from APIs the search tool
cannot reliably parse into structured numbers.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FinanceTool:
    """
    Live market data from free APIs.
    CoinGecko (crypto) and alternative.me (sentiment).
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "finance",
                "description": (
                    "Live financial market data from free APIs. "
                    "Actions: crypto (real-time price, 24h change, market cap "
                    "via CoinGecko — supports any coin), "
                    "fear_greed (Crypto Fear & Greed Index). "
                    "Informational only — not financial advice."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["crypto", "fear_greed"],
                        },
                        "symbol": {
                            "type": "string",
                            "description": (
                                "Coin id for CoinGecko: bitcoin, ethereum, "
                                "solana, dogecoin, etc."
                            ),
                        },
                        "vs_currency": {
                            "type": "string",
                            "description": "Quote currency (default: usd)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(
        self,
        action: str,
        symbol: str = "bitcoin",
        vs_currency: str = "usd",
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            import httpx
        except ImportError:
            return {"success": False, "error": "httpx required: pip install httpx"}

        try:
            if action == "crypto":
                return await self._crypto(symbol, vs_currency)
            elif action == "fear_greed":
                return await self._fear_greed()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"FinanceTool.{action} failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── CoinGecko ────────────────────────────────────────────────────

    async def _crypto(self, coin: str, vs: str) -> Dict[str, Any]:
        import httpx

        coin = (coin or "bitcoin").lower().strip().replace(" ", "-")
        vs = (vs or "usd").lower().strip()

        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": vs,
                    "ids": coin,
                    "order": "market_cap_desc",
                    "sparkline": "false",
                    "price_change_percentage": "1h,24h,7d",
                },
            )
            if resp.status_code == 429:
                return {"success": False, "error": "CoinGecko rate limit — retry in 30s"}
            if resp.status_code != 200:
                return {"success": False, "error": f"CoinGecko: HTTP {resp.status_code}"}

            data = resp.json()
            if not data:
                return {"success": False, "error": f"Coin '{coin}' not found on CoinGecko"}

            return {"success": True, "output": self._format_coin(data[0], vs)}

    def _format_coin(self, d: dict, vs: str) -> str:
        name = d.get("name", "?")
        symbol = d.get("symbol", "?").upper()
        price = d.get("current_price", 0)
        change_24h = d.get("price_change_percentage_24h", 0) or 0
        change_1h = d.get("price_change_percentage_1h_in_currency", 0) or 0
        change_7d = d.get("price_change_percentage_7d_in_currency", 0) or 0
        mcap = d.get("market_cap", 0) or 0
        volume = d.get("total_volume", 0) or 0
        high_24 = d.get("high_24h", 0) or 0
        low_24 = d.get("low_24h", 0) or 0
        ath = d.get("ath", 0) or 0
        ath_change = d.get("ath_change_percentage", 0) or 0
        rank = d.get("market_cap_rank", "?")

        arrow = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
        cur = vs.upper()

        lines = [
            f"{arrow} {name} ({symbol})  —  #{rank}",
            f"Price:   {price:>14,.6g} {cur}",
            f"24h:     {change_24h:>+13.2f}%  |  1h: {change_1h:+.2f}%  |  7d: {change_7d:+.2f}%",
            f"24h H/L: {high_24:>14,.6g} / {low_24:,.6g} {cur}",
            f"MCap:    {mcap:>14,.0f} {cur}",
            f"Volume:  {volume:>14,.0f} {cur}",
            f"ATH:     {ath:>14,.6g} {cur} ({ath_change:+.1f}%)",
        ]
        return "\n".join(lines)

    # ── Fear & Greed ─────────────────────────────────────────────────

    async def _fear_greed(self) -> Dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.alternative.me/fng/",
                params={"limit": "7", "format": "json"},
            )
            if resp.status_code != 200:
                return {"success": False, "error": f"Fear & Greed API: HTTP {resp.status_code}"}

            entries = resp.json().get("data", [])
            if not entries:
                return {"success": False, "error": "No Fear & Greed data"}

            lines = ["═══ Crypto Fear & Greed Index ═══", ""]
            for entry in entries:
                val = entry.get("value", "?")
                label = entry.get("value_classification", "?")
                ts = entry.get("timestamp", "")
                # Convert timestamp
                try:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(int(ts))
                    date_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    date_str = ts
                bar = "█" * (int(val) // 5) if str(val).isdigit() else ""
                lines.append(f"  {date_str}  {val:>3}/100  {bar}  {label}")

            today = entries[0]
            val = int(today.get("value", 50))
            if val <= 25:
                lines.append("\n⚡ Extreme Fear — historically a buy signal")
            elif val <= 40:
                lines.append("\n😰 Fear — market is nervous")
            elif val <= 60:
                lines.append("\n😐 Neutral")
            elif val <= 75:
                lines.append("\n😊 Greed — market is confident")
            else:
                lines.append("\n🔥 Extreme Greed — historically a sell signal")

            return {"success": True, "output": "\n".join(lines)}
