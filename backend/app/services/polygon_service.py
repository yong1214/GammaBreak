"""Polygon free-tier REST client (delayed quotes + aggregates)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import httpx


class PolygonService:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base = "https://api.polygon.io"

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        params = dict(params or {})
        params["apiKey"] = self.api_key
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.base}{path}", params=params)
            resp.raise_for_status()
            return resp.json()

    async def previous_close(self, symbol: str) -> Optional[float]:
        data = await self._get(f"/v2/aggs/ticker/{symbol}/prev")
        results = data.get("results") or []
        return results[0].get("c") if results else None

    async def daily_bars(self, symbol: str, lookback_days: int = 30) -> list[dict]:
        end = date.today()
        start = end - timedelta(days=lookback_days)
        data = await self._get(
            f"/v2/aggs/ticker/{symbol}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            {"adjusted": "true", "sort": "asc", "limit": 5000},
        )
        return data.get("results") or []

    async def snapshot(self, symbol: str) -> dict:
        data = await self._get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}")
        return data.get("ticker") or {}

    async def realized_volatility(self, symbol: str, lookback_days: int = 20) -> Optional[float]:
        bars = await self.daily_bars(symbol, lookback_days + 5)
        if len(bars) < 5:
            return None
        import math
        closes = [b["c"] for b in bars if "c" in b]
        rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
        if not rets:
            return None
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
        return math.sqrt(var) * math.sqrt(252)
