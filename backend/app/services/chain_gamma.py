"""Compute approximate dealer gamma walls from an IBKR option chain.

This is a free fallback for when no third-party GEX provider is configured.
The convention assumes dealers are short calls / long puts vs. retail, so:

  GEX(strike) = -call_gamma * call_OI * 100 + put_gamma * put_OI * 100

Call wall  = strike with the most negative GEX above spot (resistance)
Put wall   = strike with the most positive GEX below spot (support)
Zero gamma = strike where running cumulative GEX flips sign
"""

from __future__ import annotations

from typing import Optional

from ..models.options import GammaProfile, GammaWall, OptionChain


def gamma_profile_from_chain(chain: OptionChain) -> GammaProfile:
    spot = chain.underlying_price or 0.0

    # Aggregate per-strike GEX
    by_strike: dict[float, float] = {}
    for q in chain.quotes:
        if not q.greeks or q.greeks.gamma is None:
            continue
        oi = q.open_interest or 0
        if oi <= 0:
            # IBKR doesn't always populate OI without an extra subscription.
            # Fall back to volume so we still produce a profile in dev.
            oi = q.volume or 0
        if oi <= 0:
            continue
        sign = -1.0 if q.right == "C" else 1.0
        by_strike[q.strike] = by_strike.get(q.strike, 0.0) + sign * q.greeks.gamma * oi * 100

    if not by_strike:
        return GammaProfile(symbol=chain.symbol, spot=spot, walls=[], net_gex=0.0)

    strikes = sorted(by_strike.keys())
    net_gex = sum(by_strike.values())

    # Call wall = most negative GEX above spot
    above = [(s, g) for s, g in by_strike.items() if s >= spot]
    call_wall = min(above, key=lambda kv: kv[1])[0] if above else None

    # Put wall = most positive GEX below spot
    below = [(s, g) for s, g in by_strike.items() if s <= spot]
    put_wall = max(below, key=lambda kv: kv[1])[0] if below else None

    # Zero gamma = strike where cumulative GEX (from low → high) flips sign
    zero_gamma: Optional[float] = None
    cum = 0.0
    prev_strike: Optional[float] = None
    prev_cum: float = 0.0
    for s in strikes:
        new_cum = cum + by_strike[s]
        if prev_strike is not None and ((cum < 0 < new_cum) or (cum > 0 > new_cum)):
            # Linear interpolation between prev_strike and s
            denom = (new_cum - prev_cum) or 1.0
            zero_gamma = prev_strike + (s - prev_strike) * (-prev_cum / denom)
            break
        prev_strike, prev_cum, cum = s, cum, new_cum

    max_abs = max((abs(g) for g in by_strike.values()), default=1.0) or 1.0
    walls = []
    for s, g in sorted(by_strike.items()):
        if s == call_wall:
            wtype = "call_wall"
        elif s == put_wall:
            wtype = "put_wall"
        elif g >= 0:
            wtype = "support"
        else:
            wtype = "resistance"
        walls.append(GammaWall(
            strike=s,
            gamma_exposure=g,
            type=wtype,
            strength=min(1.0, abs(g) / max_abs),
        ))

    return GammaProfile(
        symbol=chain.symbol,
        spot=spot,
        zero_gamma=zero_gamma,
        call_wall=call_wall,
        put_wall=put_wall,
        walls=walls,
        net_gex=net_gex,
    )
