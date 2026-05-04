# GammaBreak

iPhone application for analyzing stock options with Greeks and dealer gamma
walls to predict short-horizon price action.

```
┌────────────┐   HTTPS+Bearer   ┌──────────────┐   TWS API   ┌─────────┐
│  iPhone    │  ──────────────► │  Backend     │ ──────────► │  IBKR   │
│  SwiftUI   │ ◄──────────────  │  FastAPI     │             │  TWS    │
└────────────┘                  │              │ ──HTTPS───► │ Polygon │
                                │              │ ──HTTPS───► │FlashAlpha│
                                └──────────────┘             └─────────┘
```

## Why this architecture

IBKR's TWS API is a **local TCP socket protocol** — your phone cannot reach it
directly. The Python backend runs next to TWS / IB Gateway, exposes a clean
JSON API, and adds bearer-token auth so the iPhone can connect over your LAN
or a tunnel.

The recommended starting stack:

| Layer            | Provider          | Tier     | Purpose                          |
|------------------|-------------------|----------|----------------------------------|
| Greeks + exec    | IBKR TWS API      | Free     | Per-strike Greeks, order routing |
| Gamma walls      | FlashAlpha        | Free     | Dealer GEX, call/put walls       |
| Stock price / RV | Polygon           | Free     | Snapshots, realized vol          |

Validate for $0, then upgrade to ThetaData when you're ready to go deeper on
options analytics — only `services/polygon_service.py` needs to change.

## Repo layout

```
backend/   FastAPI service: bridges IBKR + Polygon + FlashAlpha
ios/       SwiftUI iPhone app (XcodeGen project)
```

## Quick start

### 1. Backend

```bash
cd backend
cp .env.example .env       # fill in API keys + auth token + IBKR port
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Make sure TWS or IB Gateway is running with API access enabled.

### 2. iOS

```bash
cd ios
brew install xcodegen
xcodegen generate
open GammaBreak.xcodeproj
```

Build to a device or simulator, open **Settings**, point it at the backend URL
and paste the bearer token, then add tickers in the **Watchlist** tab.

## Price-action prediction

The model is intentionally rule-based and auditable. For a given symbol it:

1. Pulls the option chain (per-strike δ, γ, IV) from IBKR.
2. Aggregates dealer gamma exposure across the N nearest expiries (chain-derived) or pulls it from a paid provider if configured.
3. Pulls realized vol from Polygon (optional).
4. Computes a 1σ expected move over the chosen horizon.
5. Sets bias from spot vs. zero-gamma and proximity to the nearest wall.
6. Clamps upper/lower targets at the call and put walls.

Every prediction returns a `rationale` array so the iPhone UI can show *why*
the model chose its bias.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/quote/{symbol}` | Polygon snapshot |
| GET | `/api/chain/{symbol}` | IBKR option chain (single nearest expiry) |
| GET | `/api/gamma/{symbol}?expiries=N` | Multi-expiry dealer gamma profile |
| GET | `/api/iv-rank/{symbol}` | ATM IV + rank/percentile vs. SQLite history |
| GET | `/api/predict/{symbol}?horizon_minutes=N` | Composite price-action prediction |
| GET | `/api/account` | IBKR account summary |
| GET | `/api/positions` | Open positions with P&L |
| POST | `/api/order` | Place an option order (LMT or MKT) |

## License

MIT — see [LICENSE](LICENSE).
