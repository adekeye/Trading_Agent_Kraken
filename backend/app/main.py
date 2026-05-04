"""FastAPI application entrypoint."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .database import init_db
from .routers import auth_router, audit_router, commands_router, kraken_router


settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_per_minute])

app = FastAPI(title=settings.app_name, version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health(_: Request):
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth_router.router)
app.include_router(kraken_router.router)
app.include_router(commands_router.router)
app.include_router(audit_router.router)
