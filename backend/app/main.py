"""FastAPI application entrypoint."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .database import init_db
from .equities import get_registry
from .kraken_client import KrakenClient
from .routers import auth_router, audit_router, commands_router, kraken_router

logger = logging.getLogger(__name__)
settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_per_minute])


# How often to refresh the xStocks registry from Kraken's public AssetPairs.
EQUITY_REFRESH_INTERVAL_SECONDS = 60 * 60  # 1 hour


async def _equity_registry_loop() -> None:
    """Background task: refresh the xStocks registry on boot and every hour."""
    registry = get_registry()
    while True:
        try:
            async with KrakenClient() as kc:
                await registry.refresh(kc)
        except Exception as exc:  # registry.refresh swallows; defensive only
            logger.warning("Equity registry loop iteration failed: %s", exc)
        await asyncio.sleep(EQUITY_REFRESH_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task: asyncio.Task | None = None
    if settings.equity_registry_auto_refresh:
        task = asyncio.create_task(_equity_registry_loop(), name="equity-registry-refresh")
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(_: Request):
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth_router.router)
app.include_router(kraken_router.router)
app.include_router(commands_router.router)
app.include_router(audit_router.router)
