"""FlashAlpha free-tier client for dealer gamma exposure / gamma walls."""

from __future__ import annotations

from typing import Optional

import httpx

from ..models.options import GammaProfile, GammaWall


class FlashAlphaService:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base = base_url.rstrip("/")

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base}{path}",
                params=params or {},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def gamma_profile(self, symbol: str) -> GammaProfile:
        """Fetch the dealer gamma profile + walls for a ticker.

        FlashAlpha's free endpoint shape varies; we map defensively so a missing
        field doesn't break the iOS client.
        """
        data = await self._get("/gamma/levels", {"symbol": symbol})

        walls: list[GammaWall] = []
        max_gex = max((abs(w.get("gex", 0.0)) for w in data.get("walls", [])), default=1.0) or 1.0
        for w in data.get("walls", []):
            walls.append(GammaWall(
                strike=float(w["strike"]),
                gamma_exposure=float(w.get("gex", 0.0)),
                type=w.get("type", "support"),
                strength=min(1.0, abs(float(w.get("gex", 0.0))) / max_gex),
            ))

        return GammaProfile(
            symbol=symbol,
            spot=data.get("spot"),
            zero_gamma=data.get("zero_gamma"),
            call_wall=data.get("call_wall"),
            put_wall=data.get("put_wall"),
            walls=walls,
            net_gex=data.get("net_gex"),
        )
