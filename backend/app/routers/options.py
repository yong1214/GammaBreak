import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.options import GammaProfile, OptionChain, PricePrediction
from ..services.chain_gamma import gamma_profile_from_chain
from ..services.flashalpha_service import FlashAlphaService
from ..services.ibkr_service import IBKRService
from ..services.polygon_service import PolygonService
from ..services.price_predictor import predict
from .auth import require_token
from .deps import get_flashalpha, get_ibkr, get_polygon

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


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
) -> OptionChain:
    try:
        return await ibkr.get_option_chain(symbol.upper(), expiry, strike_window)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc


@router.get("/gamma/{symbol}", response_model=GammaProfile)
async def gamma(
    symbol: str,
    ibkr: IBKRService = Depends(get_ibkr),
    flashalpha: FlashAlphaService = Depends(get_flashalpha),
) -> GammaProfile:
    sym = symbol.upper()

    # Prefer the external provider when configured; fall back to a chain-derived
    # profile so the iOS app keeps working without a paid GEX API.
    if flashalpha.api_key:
        try:
            return await flashalpha.gamma_profile(sym)
        except Exception as exc:
            logger.warning("FlashAlpha unavailable, falling back to chain GEX: %s", exc)

    try:
        chain_data = await ibkr.get_option_chain(sym)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IBKR error: {exc}") from exc
    return gamma_profile_from_chain(chain_data)


@router.get("/predict/{symbol}", response_model=PricePrediction)
async def predict_price(
    symbol: str,
    horizon_minutes: int = Query(default=60, ge=5, le=1440),
    expiry: Optional[date] = Query(default=None),
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
        gamma_profile = gamma_profile_from_chain(chain_data)

    rv = None
    if polygon.api_key:
        try:
            rv = await polygon.realized_volatility(sym)
        except Exception as exc:
            logger.warning("Polygon unavailable: %s", exc)

    return predict(chain_data, gamma_profile, rv, horizon_minutes)
