# GammaBreak Backend

FastAPI service that bridges the iPhone app to IBKR TWS (Greeks + execution),
FlashAlpha (gamma walls), and Polygon (stock quotes / realized vol).

## Why a backend?

IBKR's TWS API is a local TCP socket protocol that the iPhone cannot reach
directly. This service runs next to TWS / IB Gateway, exposes a clean HTTPS
JSON API, and adds bearer-token auth so the phone can talk to it over the
network.

## Run locally

```bash
cd backend
cp .env.example .env          # fill in API keys + auth token
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Make sure TWS or IB Gateway is running, has the API enabled (Edit → Global
Configuration → API → Settings: "Enable ActiveX and Socket Clients"), and is
on the port set in `.env` (default 7497 = paper trading).

## Run with Docker

```bash
docker compose up --build
```

On macOS / Windows set `IBKR_HOST=host.docker.internal` in `.env` so the
container can reach the TWS instance running on the host.

## Endpoints

All endpoints require `Authorization: Bearer <API_AUTH_TOKEN>`.

- `GET /health` — liveness check
- `GET /api/quote/{symbol}` — Polygon snapshot
- `GET /api/chain/{symbol}?expiry=YYYY-MM-DD&strike_window=10` — IBKR option chain with Greeks
- `GET /api/gamma/{symbol}` — FlashAlpha dealer gamma profile + walls
- `GET /api/predict/{symbol}?horizon_minutes=60` — composite price-action prediction
