"""Black-Scholes Greeks fallback used when the broker doesn't return them."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm


@dataclass
class BSInputs:
    spot: float
    strike: float
    time_to_expiry: float  # years
    rate: float            # risk-free
    iv: float              # implied vol
    is_call: bool


def _d1_d2(p: BSInputs) -> tuple[float, float]:
    if p.iv <= 0 or p.time_to_expiry <= 0:
        return float("nan"), float("nan")
    sqrt_t = math.sqrt(p.time_to_expiry)
    d1 = (math.log(p.spot / p.strike) + (p.rate + 0.5 * p.iv ** 2) * p.time_to_expiry) / (p.iv * sqrt_t)
    d2 = d1 - p.iv * sqrt_t
    return d1, d2


def black_scholes_greeks(p: BSInputs) -> dict[str, float]:
    d1, d2 = _d1_d2(p)
    if math.isnan(d1):
        return {"delta": float("nan"), "gamma": float("nan"), "theta": float("nan"),
                "vega": float("nan"), "rho": float("nan")}

    pdf_d1 = norm.pdf(d1)
    sqrt_t = math.sqrt(p.time_to_expiry)
    discount = math.exp(-p.rate * p.time_to_expiry)

    if p.is_call:
        delta = norm.cdf(d1)
        rho = p.strike * p.time_to_expiry * discount * norm.cdf(d2) / 100
        theta = (-(p.spot * pdf_d1 * p.iv) / (2 * sqrt_t)
                 - p.rate * p.strike * discount * norm.cdf(d2)) / 365
    else:
        delta = norm.cdf(d1) - 1
        rho = -p.strike * p.time_to_expiry * discount * norm.cdf(-d2) / 100
        theta = (-(p.spot * pdf_d1 * p.iv) / (2 * sqrt_t)
                 + p.rate * p.strike * discount * norm.cdf(-d2)) / 365

    gamma = pdf_d1 / (p.spot * p.iv * sqrt_t)
    vega = p.spot * pdf_d1 * sqrt_t / 100

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}
