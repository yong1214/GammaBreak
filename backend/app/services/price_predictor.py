"""Predict short-horizon price action from option Greeks + dealer gamma walls.

The model is intentionally transparent (rule-based) so traders can audit each
factor that contributed to the bias.

Inputs:
- option chain (per-strike gamma + IV + open interest)
- dealer gamma profile (zero-gamma, call wall, put wall)
- realized vol (Polygon)

Outputs a horizon-conditioned expected move plus a directional bias.
"""

from __future__ import annotations

import math
from typing import Optional

from ..models.options import (
    GammaProfile,
    OptionChain,
    PricePrediction,
)


def _atm_iv(chain: OptionChain) -> Optional[float]:
    if not chain.underlying_price or not chain.quotes:
        return None
    spot = chain.underlying_price
    closest = sorted(chain.quotes, key=lambda q: abs(q.strike - spot))
    for q in closest:
        if q.greeks and q.greeks.iv:
            return q.greeks.iv
    return None


def _net_dealer_gamma(chain: OptionChain) -> float:
    """Approximate net dealer gamma exposure from the chain.

    Convention: dealers are typically short calls / long puts vs. retail, so we
    subtract call gamma and add put gamma weighted by open interest.
    """
    total = 0.0
    for q in chain.quotes:
        if not q.greeks or q.greeks.gamma is None:
            continue
        oi = q.open_interest or 0
        sign = -1.0 if q.right == "C" else 1.0
        total += sign * q.greeks.gamma * oi * 100
    return total


def predict(
    chain: OptionChain,
    gamma_profile: Optional[GammaProfile],
    realized_vol: Optional[float],
    horizon_minutes: int = 60,
) -> PricePrediction:
    spot = chain.underlying_price or 0.0
    if spot <= 0:
        raise ValueError("Underlying price required for prediction")

    rationale: list[str] = []

    iv = _atm_iv(chain) or realized_vol or 0.20
    rationale.append(f"ATM IV ~ {iv:.1%}")

    horizon_years = horizon_minutes / (60 * 24 * 252)
    expected_move = spot * iv * math.sqrt(horizon_years)
    rationale.append(f"1σ move over {horizon_minutes}m ≈ ${expected_move:.2f}")

    bias = "neutral"
    confidence = 0.4

    net_gex_chain = _net_dealer_gamma(chain)
    rationale.append(f"Chain-implied dealer GEX: {net_gex_chain:,.0f}")

    if gamma_profile:
        if gamma_profile.zero_gamma is not None:
            if spot > gamma_profile.zero_gamma:
                rationale.append(
                    f"Spot {spot:.2f} above zero-gamma {gamma_profile.zero_gamma:.2f} — "
                    "dealers long gamma, expect mean-reversion / pinning"
                )
                bias = "pinned"
                confidence = 0.6
            else:
                rationale.append(
                    f"Spot {spot:.2f} below zero-gamma {gamma_profile.zero_gamma:.2f} — "
                    "dealers short gamma, moves can accelerate"
                )
                confidence = 0.55

        if gamma_profile.call_wall and spot < gamma_profile.call_wall:
            dist = (gamma_profile.call_wall - spot) / spot
            rationale.append(f"Call wall {gamma_profile.call_wall:.2f} ({dist:+.2%}) caps upside")
            if dist < 0.005:
                bias = "bearish"
                confidence = max(confidence, 0.65)
        if gamma_profile.put_wall and spot > gamma_profile.put_wall:
            dist = (spot - gamma_profile.put_wall) / spot
            rationale.append(f"Put wall {gamma_profile.put_wall:.2f} ({-dist:+.2%}) supports downside")
            if dist < 0.005:
                bias = "bullish"
                confidence = max(confidence, 0.65)

    if bias == "neutral" and net_gex_chain > 0:
        bias = "pinned"
        rationale.append("Positive chain GEX — sideways/pin-to-strike bias")
    elif bias == "neutral" and net_gex_chain < 0:
        bias = "neutral"
        rationale.append("Negative chain GEX — directional follow-through likelier")

    upper_target = spot + expected_move
    lower_target = spot - expected_move
    if gamma_profile and gamma_profile.call_wall:
        upper_target = min(upper_target, gamma_profile.call_wall)
    if gamma_profile and gamma_profile.put_wall:
        lower_target = max(lower_target, gamma_profile.put_wall)

    return PricePrediction(
        symbol=chain.symbol,
        spot=spot,
        horizon_minutes=horizon_minutes,
        expected_move=expected_move,
        upper_target=upper_target,
        lower_target=lower_target,
        bias=bias,
        confidence=min(0.95, confidence),
        rationale=rationale,
    )
