import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import options
from .routers.deps import get_ibkr

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    ibkr = get_ibkr(settings)
    yield
    await ibkr.disconnect()


app = FastAPI(title="GammaBreak Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(options.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
