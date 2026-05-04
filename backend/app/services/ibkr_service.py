"""IBKR TWS bridge using ib_insync.

The TWS desktop or IB Gateway must be running on the host machine with the
API enabled. This service connects on demand and caches the client.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import date, datetime
from typing import Optional

from ib_insync import IB, LimitOrder, MarketOrder, Option, Order, Stock, Ticker

from ..models.options import Greeks, OptionChain, OptionQuote

logger = logging.getLogger(__name__)


def _is_real(x) -> bool:
    """True iff x is a finite real number (filters NaN, None, inf)."""
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


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
                # 1=live (needs subscription), 2=frozen, 3=delayed (free, 15-min),
                # 4=delayed-frozen (free, works after hours). 4 is the safest default
                # for paper accounts without market-data subscriptions.
                self._ib.reqMarketDataType(4)
        return self._ib

    async def disconnect(self) -> None:
        if self._ib.isConnected():
            self._ib.disconnect()

    async def get_underlying_price(self, symbol: str) -> Optional[float]:
        ib = await self._ensure_connected()
        contract = Stock(symbol, "SMART", "USD")
        await ib.qualifyContractsAsync(contract)

        ticker = ib.reqMktData(contract, "", False, False)
        # Wait up to ~6s for any of last/close/midpoint to populate.
        for _ in range(12):
            await asyncio.sleep(0.5)
            for candidate in (ticker.last, ticker.close, ticker.marketPrice()):
                if _is_real(candidate) and candidate > 0:
                    ib.cancelMktData(contract)
                    logger.info("%s spot via mkt-data: %.4f", symbol, candidate)
                    return float(candidate)
        ib.cancelMktData(contract)

        # Fallback: ask for the last historical close (works even with no
        # subscription and outside trading hours).
        try:
            bars = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr="2 D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            if bars and _is_real(bars[-1].close):
                logger.info("%s spot via historical close: %.4f", symbol, bars[-1].close)
                return float(bars[-1].close)
        except Exception as exc:
            logger.warning("Historical fallback failed for %s: %s", symbol, exc)

        return None

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

        # Prefer the SMART chain whose tradingClass matches the symbol; fall
        # back to any SMART chain, then anything. This avoids picking a
        # sibling class (e.g. SPXW) whose strikes/expirations don't apply.
        chain = (
            next((p for p in params if p.exchange == "SMART" and p.tradingClass == symbol), None)
            or next((p for p in params if p.exchange == "SMART"), None)
            or params[0]
        )
        logger.info("Using chain exchange=%s tradingClass=%s", chain.exchange, chain.tradingClass)

        today = date.today()
        all_expiries = sorted({datetime.strptime(e, "%Y%m%d").date() for e in chain.expirations})
        future_expiries = [e for e in all_expiries if e >= today]
        if not future_expiries:
            raise RuntimeError(f"No future expirations for {symbol}")
        target_expiry = expiry or future_expiries[0]
        target_expiry_str = target_expiry.strftime("%Y%m%d")

        spot = await self.get_underlying_price(symbol)
        if not _is_real(spot) or spot <= 0:
            raise RuntimeError(
                f"Could not retrieve spot price for {symbol}. "
                "Check that IB Gateway is logged in and the symbol trades. "
                "If you have no market-data subscription, the delayed-frozen "
                "fallback should still work — try again during/after a trading day."
            )

        # Strikes returned by reqSecDefOptParams are the union across all
        # expiries. Limit to ±15% of spot, then pick N nearest on each side.
        viable = sorted(float(s) for s in chain.strikes if 0.85 * spot <= float(s) <= 1.15 * spot)
        if not viable:
            # Spot is real but very far from any listed strike (rare). Widen the band.
            viable = sorted(float(s) for s in chain.strikes if 0.5 * spot <= float(s) <= 1.5 * spot)
        nearest = sorted(sorted(viable, key=lambda s: abs(s - spot))[: strike_window * 2])
        logger.info("%s spot=%.2f, %d viable strikes, %d selected", symbol, spot, len(viable), len(nearest))

        candidates = [
            Option(symbol, target_expiry_str, strike, right, "SMART", tradingClass=symbol)
            for strike in nearest
            for right in ("C", "P")
        ]

        # Qualify in one round-trip; IBKR fills conId on success and leaves it
        # 0 on failure. Drop failures so reqTickers isn't called on bad ones.
        await ib.qualifyContractsAsync(*candidates)
        qualified = [c for c in candidates if c.conId]
        skipped = len(candidates) - len(qualified)
        if skipped:
            logger.info("Skipped %d unqualified contracts for %s %s",
                        skipped, symbol, target_expiry_str)
        if not qualified:
            raise RuntimeError(
                f"No tradable strikes for {symbol} on {target_expiry}. "
                f"Picked {len(nearest)} strikes around spot {spot:.2f}; "
                "the chain class may be wrong, or this expiry has no listings."
            )

        tickers = await ib.reqTickersAsync(*qualified)
        quotes = [self._ticker_to_quote(t, symbol, target_expiry, spot) for t in tickers]

        return OptionChain(
            symbol=symbol,
            underlying_price=spot,
            expiries=future_expiries,
            quotes=quotes,
        )

    async def get_multi_expiry_chain(
        self,
        symbol: str,
        num_expiries: int = 3,
        strike_window: int = 8,
    ) -> OptionChain:
        """Fetch the N nearest future expiries and merge into one OptionChain.

        Strikes are reused across expiries; tickers are requested in one batch
        to keep the round-trip count low. Used by the multi-expiry GEX route.
        """
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

        chain = (
            next((p for p in params if p.exchange == "SMART" and p.tradingClass == symbol), None)
            or next((p for p in params if p.exchange == "SMART"), None)
            or params[0]
        )

        today = date.today()
        all_expiries = sorted({datetime.strptime(e, "%Y%m%d").date() for e in chain.expirations})
        future_expiries = [e for e in all_expiries if e >= today][:num_expiries]
        if not future_expiries:
            raise RuntimeError(f"No future expirations for {symbol}")

        spot = await self.get_underlying_price(symbol)
        if not _is_real(spot) or spot <= 0:
            raise RuntimeError(f"Could not retrieve spot price for {symbol}")

        viable = sorted(float(s) for s in chain.strikes if 0.9 * spot <= float(s) <= 1.1 * spot)
        if not viable:
            viable = sorted(float(s) for s in chain.strikes if 0.7 * spot <= float(s) <= 1.3 * spot)
        nearest = sorted(sorted(viable, key=lambda s: abs(s - spot))[: strike_window * 2])

        candidates = [
            Option(symbol, exp.strftime("%Y%m%d"), strike, right, "SMART", tradingClass=symbol)
            for exp in future_expiries
            for strike in nearest
            for right in ("C", "P")
        ]
        await ib.qualifyContractsAsync(*candidates)
        qualified = [c for c in candidates if c.conId]
        if not qualified:
            raise RuntimeError(f"No tradable strikes for {symbol} across {len(future_expiries)} expiries")

        logger.info(
            "%s multi-expiry: spot=%.2f, %d expiries, %d strikes, %d/%d qualified",
            symbol, spot, len(future_expiries), len(nearest), len(qualified), len(candidates),
        )

        tickers = await ib.reqTickersAsync(*qualified)
        quotes = []
        for t in tickers:
            try:
                exp_str = t.contract.lastTradeDateOrContractMonth
                exp_date = datetime.strptime(exp_str, "%Y%m%d").date()
            except (ValueError, AttributeError):
                continue
            quotes.append(self._ticker_to_quote(t, symbol, exp_date, spot))

        return OptionChain(
            symbol=symbol,
            underlying_price=spot,
            expiries=future_expiries,
            quotes=quotes,
        )

    @staticmethod
    def _ticker_to_quote(t: Ticker, symbol: str, expiry: date, spot: float) -> OptionQuote:
        c = t.contract
        mg = t.modelGreeks or t.lastGreeks or t.bidGreeks or t.askGreeks
        greeks = Greeks(
            delta=getattr(mg, "delta", None) if mg else None,
            gamma=getattr(mg, "gamma", None) if mg else None,
            theta=getattr(mg, "theta", None) if mg else None,
            vega=getattr(mg, "vega", None) if mg else None,
            iv=getattr(mg, "impliedVol", None) if mg else None,
        )

        def _pos(v):
            return float(v) if _is_real(v) and v > 0 else None

        return OptionQuote(
            symbol=symbol,
            expiry=expiry,
            strike=float(c.strike),
            right=c.right,
            bid=_pos(t.bid),
            ask=_pos(t.ask),
            last=_pos(t.last),
            volume=int(t.volume) if _is_real(t.volume) and t.volume > 0 else None,
            underlying_price=spot,
            greeks=greeks,
        )

    async def get_positions(self) -> list[dict]:
        ib = await self._ensure_connected()
        portfolio = ib.portfolio()
        out: list[dict] = []
        for item in portfolio:
            c = item.contract
            out.append({
                "symbol": c.symbol,
                "sec_type": c.secType,
                "right": getattr(c, "right", None),
                "strike": getattr(c, "strike", None),
                "expiry": getattr(c, "lastTradeDateOrContractMonth", None) or None,
                "position": float(item.position),
                "avg_cost": float(item.averageCost),
                "market_price": float(item.marketPrice) if _is_real(item.marketPrice) else None,
                "market_value": float(item.marketValue) if _is_real(item.marketValue) else None,
                "unrealized_pnl": float(item.unrealizedPNL) if _is_real(item.unrealizedPNL) else None,
                "realized_pnl": float(item.realizedPNL) if _is_real(item.realizedPNL) else None,
            })
        return out

    async def get_account_summary(self) -> dict:
        ib = await self._ensure_connected()
        rows = ib.accountSummary()
        wanted = {
            "NetLiquidation", "BuyingPower", "AvailableFunds",
            "TotalCashValue", "GrossPositionValue", "MaintMarginReq",
        }
        out: dict[str, float] = {}
        for r in rows:
            if r.tag in wanted:
                try:
                    out[r.tag] = float(r.value)
                except ValueError:
                    pass
        return out

    async def place_option_order(
        self,
        symbol: str,
        expiry: date,
        strike: float,
        right: str,
        action: str,         # "BUY" or "SELL"
        quantity: int,
        order_type: str = "LMT",   # "LMT" or "MKT"
        limit_price: Optional[float] = None,
    ) -> dict:
        ib = await self._ensure_connected()
        contract = Option(
            symbol, expiry.strftime("%Y%m%d"), strike, right, "SMART",
            tradingClass=symbol,
        )
        await ib.qualifyContractsAsync(contract)
        if not contract.conId:
            raise RuntimeError(f"Could not qualify {symbol} {expiry} {strike}{right}")

        action = action.upper()
        if action not in ("BUY", "SELL"):
            raise ValueError("action must be BUY or SELL")

        if order_type.upper() == "MKT":
            order = MarketOrder(action, quantity)
        else:
            if limit_price is None:
                raise ValueError("limit_price required for LMT orders")
            order = LimitOrder(action, quantity, round(float(limit_price), 2))

        trade = ib.placeOrder(contract, order)
        # Give IBKR a moment to acknowledge
        await asyncio.sleep(0.5)
        return {
            "order_id": trade.order.orderId,
            "perm_id": trade.order.permId,
            "status": trade.orderStatus.status,
            "filled": float(trade.orderStatus.filled),
            "remaining": float(trade.orderStatus.remaining),
            "avg_fill_price": float(trade.orderStatus.avgFillPrice or 0.0),
            "symbol": symbol,
            "strike": strike,
            "right": right,
            "expiry": expiry.isoformat(),
            "action": action,
            "quantity": quantity,
            "order_type": order_type.upper(),
            "limit_price": limit_price,
        }
