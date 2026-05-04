from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    app_name: str = Field(default="Kraken Trading Agent")

    database_url: str = Field(default="sqlite:///./trading_agent.db")

    jwt_secret: str = Field(default="change-me-in-production-please-use-a-long-random-value")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_minutes: int = Field(default=60 * 8)

    # Fernet key (urlsafe base64-encoded 32 bytes). MUST be set in production.
    encryption_key: str = Field(default="")

    kraken_api_url: str = Field(default="https://api.kraken.com")
    kraken_request_timeout_seconds: float = Field(default=15.0)

    # Risk engine defaults (overridable per-user via Settings table)
    default_max_order_notional_usd: float = Field(default=1000.0)
    default_dry_run: bool = Field(default=True)
    default_trading_enabled: bool = Field(default=True)
    large_order_threshold_usd: float = Field(default=5000.0)

    cors_origins: List[str] = Field(default=["http://localhost:3000"])

    rate_limit_per_minute: str = Field(default="60/minute")

    # If false, the FastAPI lifespan will not spawn the background task that
    # refreshes the xStocks registry from Kraken's public AssetPairs. Tests
    # set this to false to keep the suite offline; production keeps it true.
    equity_registry_auto_refresh: bool = Field(default=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
