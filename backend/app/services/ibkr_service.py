"""IBKR TWS bridge using ib_insync.

The TWS desktop or IB Gateway must be running on the host machine with the
API enabled. This service connects on demand and caches the client.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Optional

from ib_insync import IB, Index, Option, Stock, Ticker

from ..models.options import Greeks, OptionChain, OptionQuote

logger = logging.getLogger(__name__)


class IBKRService:
    def __init__(self, host: str, port: int, client_id: int) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self._ib = IB()
        self._lock = asyncio.Lock()

    async def _ensure_connected(self) -> IB:
        async with self._lock:
            if not self._ib.isConnected():
                logger.info("Connecting to IBKR at %s:%s id=%s", self.host, self.port, self.client_id)
                await self._ib.connectAsync(self.host, self.port, clientId=self.client_id, timeout=10)
        return self._ib

    async def disconnect(self) -> None:
        if self._ib.isConnected():
            self._ib.disconnect()

    async def get_underlying_price(self, symbol: str) -> Optional[float]:
        ib = await self._ensure_connected()
        contract = Stock(symbol, "SMART", "USD")
        await ib.qualifyContractsAsync(contract)
        ticker = ib.reqMktData(contract, "", False, False)
        await asyncio.sleep(1.5)
        price = ticker.last or ticker.close or ticker.marketPrice()
        ib.cancelMktData(contract)
        return float(price) if price else None

    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[date] = None,
        strike_window: int = 10,
    ) -> OptionChain:
        ib = await self._ensure_connected()
        underlying = Stock(symbol, "SMART", "USD")
        await ib.qualifyContractsAsync(underlying)

        params = await ib.reqSecDefOptParamsAsync(
            underlyingSymbol=symbol,
            futFopExchange="",
            underlyingSecType="STK",
            underlyingConId=underlying.conId,
        )
        if not params:
            raise RuntimeError(f"No option parameters returned for {symbol}")

        smart = next((p for p in params if p.exchange == "SMART"), params[0])
        expiries = sorted({datetime.strptime(e, "%Y%m%d").date() for e in smart.expirations})
        target_expiry = expiry or expiries[0]
        target_expiry_str = target_expiry.strftime("%Y%m%d")

        spot = await self.get_underlying_price(symbol)
        if spot is None:
            raise RuntimeError(f"Could not retrieve spot price for {symbol}")

        # Pick the N strikes closest to spot on each side
        all_strikes = sorted(float(s) for s in smart.strikes)
        nearest = sorted(all_strikes, key=lambda s: abs(s - spot))[: strike_window * 2]
        nearest = sorted(nearest)

        contracts = []
        for strike in nearest:
            for right in ("C", "P"):
                contracts.append(Option(symbol, target_expiry_str, strike, right, "SMART"))

        await ib.qualifyContractsAsync(*contracts)
        tickers = await ib.reqTickersAsync(*contracts)

        quotes = [self._ticker_to_quote(t, symbol, target_expiry, spot) for t in tickers]

        return OptionChain(
            symbol=symbol,
            underlying_price=spot,
            expiries=expiries,
            quotes=quotes,
        )

    @staticmethod
    def _ticker_to_quote(t: Ticker, symbol: str, expiry: date, spot: float) -> OptionQuote:
        c = t.contract
        mg = t.modelGreeks or t.lastGreeks or t.bidGreeks or t.askGreeks
        greeks = Greeks(
            delta=getattr(mg, "delta", None),
            gamma=getattr(mg, "gamma", None),
            theta=getattr(mg, "theta", None),
            vega=getattr(mg, "vega", None),
            iv=getattr(mg, "impliedVol", None),
        ) if mg else Greeks()

        return OptionQuote(
            symbol=symbol,
            expiry=expiry,
            strike=float(c.strike),
            right=c.right,
            bid=t.bid if t.bid and t.bid > 0 else None,
            ask=t.ask if t.ask and t.ask > 0 else None,
            last=t.last if t.last and t.last > 0 else None,
            volume=int(t.volume) if t.volume else None,
            underlying_price=spot,
            greeks=greeks,
        )
