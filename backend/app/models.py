from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kraken_credentials: Mapped["KrakenCredential"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list["OrderRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class KrakenCredential(Base):
    __tablename__ = "kraken_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="kraken_credentials")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    trading_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_order_notional_usd: Mapped[float] = mapped_column(Float, default=1000.0)
    preferred_quote_currency: Mapped[str] = mapped_column(String(8), default="USD")
    require_two_step_for_large_orders: Mapped[bool] = mapped_column(Boolean, default=True)
    large_order_threshold_usd: Mapped[float] = mapped_column(Float, default=5000.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="settings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    raw_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="audit_logs")


class OrderRecord(Base):
    """Local mirror of orders submitted (or simulated) by this app."""

    __tablename__ = "order_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kraken_txid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pair: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), default="limit")
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    limit_price: Mapped[float] = mapped_column(Float, nullable=False)
    notional_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    raw_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="orders")


class PendingConfirmation(Base):
    """A parsed-and-validated order awaiting explicit user confirmation."""

    __tablename__ = "pending_confirmations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    raw_command: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    requires_two_step: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
