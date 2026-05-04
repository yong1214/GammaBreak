import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..models.options import GammaProfile, OptionChain, PricePrediction
from ..services.chain_gamma import gamma_profile_from_chain
from ..services.flashalpha_service import FlashAlphaService
from ..services.ibkr_service import IBKRService
from ..services.iv_history import IVHistoryStore
from ..services.polygon_service import PolygonService
from ..services.price_predictor import predict
from .auth import require_token
from .deps import get_flashalpha, get_ibkr, get_iv_store, get_polygon

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


def _atm_iv(chain: OptionChain) -> Optional[float]:
    if not chain.underlying_price or not chain.quotes:
        return None
    spot = chain.underlying_price
    for q in sorted(chain.quotes, key=lambda q: abs(q.strike - spot)):
        if q.greeks and q.greeks.iv:
            return float(q.greeks.iv)
    return None


@router.get("/quote/{symbol}")
async def quote(symbol: str, polygon: PolygonService = Depends(get_polygon)) -> dict:
    snap = await polygon.snapshot(symbol)
    return {
        "symbol": symbol,
        "last": (snap.get("lastTrade") or {}).get("p"),
        "day": snap.get("day"),
        "prev_day": snap.get("prevDay"),
        "updated": snap.get("updated"),
    }


@router.get("/chain/{symbol}", response_model=OptionChain)
async def chain(
    symbol: str,
    expiry: Optional[date] = Query(default=None),
    strike_window: int = Query(default=10, ge=1, le=50),
    ibkr: IBKRService = Depends(get_ibkr),
    iv_store: IVHistoryStore = Depends(get_iv_store),
) -> OptionChain:
    try:
        c = await ibkr.get_option_chain(symbol.upper(), expiry, strike_window)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc

    iv = _atm_iv(c)
    if iv:
        try:
            iv_store.record(symbol.upper(), iv)
        except Exception as exc:
            logger.warning("IV snapshot failed: %s", exc)
    return c


@router.get("/gamma/{symbol}", response_model=GammaProfile)
async def gamma(
    symbol: str,
    expiries: int = Query(default=3, ge=1, le=8, description="Number of nearest expiries to aggregate"),
    ibkr: IBKRService = Depends(get_ibkr),
    flashalpha: FlashAlphaService = Depends(get_flashalpha),
) -> GammaProfile:
    sym = symbol.upper()

    if flashalpha.api_key:
        try:
            return await flashalpha.gamma_profile(sym)
        except Exception as exc:
            logger.warning("FlashAlpha unavailable, falling back to chain GEX: %s", exc)

    try:
        chain_data = await ibkr.get_multi_expiry_chain(sym, num_expiries=expiries)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc
    return gamma_profile_from_chain(chain_data)


@router.get("/iv-rank/{symbol}")
async def iv_rank(
    symbol: str,
    lookback_days: int = Query(default=252, ge=10, le=730),
    ibkr: IBKRService = Depends(get_ibkr),
    iv_store: IVHistoryStore = Depends(get_iv_store),
) -> dict:
    sym = symbol.upper()
    try:
        chain_data = await ibkr.get_option_chain(sym)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc

    iv = _atm_iv(chain_data)
    if iv is None:
        raise HTTPException(status_code=503, detail="ATM IV unavailable from chain")

    iv_store.record(sym, iv)
    rank = iv_store.rank(sym, iv, lookback_days)
    if rank is None:
        return {
            "symbol": sym,
            "current_iv": iv,
            "rank": None,
            "percentile": None,
            "samples": len(iv_store.history(sym, lookback_days)),
            "message": "Insufficient history (need ≥5 hourly samples). Keep hitting /api/chain or /api/iv-rank to build history.",
        }
    return {"symbol": sym, **rank}


@router.get("/predict/{symbol}", response_model=PricePrediction)
async def predict_price(
    symbol: str,
    horizon_minutes: int = Query(default=60, ge=5, le=1440),
    expiry: Optional[date] = Query(default=None),
    expiries: int = Query(default=3, ge=1, le=8),
    ibkr: IBKRService = Depends(get_ibkr),
    flashalpha: FlashAlphaService = Depends(get_flashalpha),
    polygon: PolygonService = Depends(get_polygon),
) -> PricePrediction:
    sym = symbol.upper()
    try:
        chain_data = await ibkr.get_option_chain(sym, expiry)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc

    gamma_profile = None
    if flashalpha.api_key:
        try:
            gamma_profile = await flashalpha.gamma_profile(sym)
        except Exception as exc:
            logger.warning("FlashAlpha unavailable: %s", exc)
    if gamma_profile is None:
        try:
            multi = await ibkr.get_multi_expiry_chain(sym, num_expiries=expiries)
            gamma_profile = gamma_profile_from_chain(multi)
        except Exception:
            gamma_profile = gamma_profile_from_chain(chain_data)

    rv = None
    if polygon.api_key:
        try:
            rv = await polygon.realized_volatility(sym)
        except Exception as exc:
            logger.warning("Polygon unavailable: %s", exc)

    return predict(chain_data, gamma_profile, rv, horizon_minutes)


@router.get("/account")
async def account(ibkr: IBKRService = Depends(get_ibkr)) -> dict:
    try:
        return await ibkr.get_account_summary()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc


@router.get("/positions")
async def positions(ibkr: IBKRService = Depends(get_ibkr)) -> list[dict]:
    try:
        return await ibkr.get_positions()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc


class OrderRequest(BaseModel):
    symbol: str
    expiry: date
    strike: float
    right: str = Field(pattern="^[CP]$")
    action: str = Field(pattern="^(BUY|SELL)$")
    quantity: int = Field(ge=1, le=10000)
    order_type: str = Field(default="LMT", pattern="^(LMT|MKT)$")
    limit_price: Optional[float] = None


@router.post("/order")
async def place_order(
    req: OrderRequest,
    ibkr: IBKRService = Depends(get_ibkr),
) -> dict:
    try:
        return await ibkr.place_option_order(
            symbol=req.symbol.upper(),
            expiry=req.expiry,
            strike=req.strike,
            right=req.right,
            action=req.action,
            quantity=req.quantity,
            order_type=req.order_type,
            limit_price=req.limit_price,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR order error: {exc}") from exc
