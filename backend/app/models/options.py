from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

OptionRight = Literal["C", "P"]


class Greeks(BaseModel):
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    iv: Optional[float] = Field(default=None, description="Implied volatility")


class OptionQuote(BaseModel):
    symbol: str
    expiry: date
    strike: float
    right: OptionRight
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    underlying_price: Optional[float] = None
    greeks: Greeks = Greeks()


class OptionChain(BaseModel):
    symbol: str
    underlying_price: Optional[float]
    expiries: list[date]
    quotes: list[OptionQuote]


class GammaWall(BaseModel):
    strike: float
    gamma_exposure: float
    type: Literal["call_wall", "put_wall", "zero_gamma", "support", "resistance"]
    strength: float = Field(ge=0, le=1, description="Normalized 0..1 strength")


class GammaProfile(BaseModel):
    symbol: str
    spot: Optional[float]
    zero_gamma: Optional[float] = None
    call_wall: Optional[float] = None
    put_wall: Optional[float] = None
    walls: list[GammaWall] = []
    net_gex: Optional[float] = None


class PricePrediction(BaseModel):
    symbol: str
    spot: float
    horizon_minutes: int
    expected_move: float
    upper_target: float
    lower_target: float
    bias: Literal["bullish", "bearish", "neutral", "pinned"]
    confidence: float = Field(ge=0, le=1)
    rationale: list[str]
