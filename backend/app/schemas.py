from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------- Kraken connection ----------

class KrakenConnectRequest(BaseModel):
    api_key: str = Field(min_length=8)
    api_secret: str = Field(min_length=8)


class KrakenConnectResponse(BaseModel):
    connected: bool
    message: str


# ---------- Parsed command ----------

Intent = Literal[
    "place_order",
    "cancel_order",
    "show_orders",
    "show_balances",
    "show_history",
    "unknown",
]


OrderType = Literal["limit", "stop-loss-limit", "take-profit-limit"]


class ParsedCommand(BaseModel):
    """Structured representation of a natural-language trading command."""

    intent: Intent = "unknown"
    side: Optional[Literal["buy", "sell"]] = None
    asset: Optional[str] = None
    quote_currency: Optional[str] = None
    quantity: Optional[float] = None
    notional_amount: Optional[float] = None
    limit_price: Optional[float] = None
    # Trigger price for conditional orders (stop-loss-limit / take-profit-limit).
    # Maps to Kraken's `price` field; the limit_price maps to `price2`.
    trigger_price: Optional[float] = None
    order_type: Optional[OrderType] = None
    cancel_txid: Optional[str] = None

    confidence: float = 0.0
    requires_confirmation: bool = True
    rejection_reason: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=512)


# ---------- Preview / Confirm ----------

class OrderPreview(BaseModel):
    confirmation_id: str
    pair: str
    side: Literal["buy", "sell"]
    order_type: OrderType = "limit"
    volume: float
    limit_price: float
    # Set only for stop-loss-limit / take-profit-limit. The order fires when
    # the market crosses this trigger; once filled it's a limit at limit_price.
    trigger_price: Optional[float] = None
    notional_value: float
    quote_currency: str
    fees_estimate: Optional[float] = None
    dry_run: bool
    requires_two_step: bool
    warnings: list[str] = []
    expires_at: datetime


class ConfirmRequest(BaseModel):
    confirmation_id: str
    confirm: bool = True
    # Required only if requires_two_step is True
    second_factor_phrase: Optional[str] = None


class OrderResult(BaseModel):
    success: bool
    dry_run: bool
    kraken_txid: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None


# ---------- Direct order submission ----------

class PlaceOrderRequest(BaseModel):
    pair: str
    side: Literal["buy", "sell"]
    volume: float = Field(gt=0)
    limit_price: float = Field(gt=0)
    confirm: bool = False  # used by /kraken/place-order direct path


class CancelOrderRequest(BaseModel):
    txid: str = Field(min_length=4)


# ---------- Balances / Orders read ----------

class BalanceItem(BaseModel):
    asset: str
    amount: float


class BalancesResponse(BaseModel):
    balances: list[BalanceItem]


class OpenOrderItem(BaseModel):
    txid: str
    pair: str
    side: str
    order_type: str
    volume: float
    price: float
    status: str
    opened_at: Optional[datetime] = None


class OpenOrdersResponse(BaseModel):
    orders: list[OpenOrderItem]


class HistoryItem(BaseModel):
    txid: str
    pair: str
    side: str
    order_type: str
    volume: float
    price: float
    status: str
    closed_at: Optional[datetime] = None


class HistoryResponse(BaseModel):
    orders: list[HistoryItem]


# ---------- Settings ----------

class UserSettingsModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dry_run: bool
    trading_enabled: bool
    max_order_notional_usd: float
    preferred_quote_currency: str
    require_two_step_for_large_orders: bool
    large_order_threshold_usd: float


class UserSettingsUpdate(BaseModel):
    dry_run: Optional[bool] = None
    trading_enabled: Optional[bool] = None
    max_order_notional_usd: Optional[float] = Field(default=None, ge=0)
    preferred_quote_currency: Optional[str] = None
    require_two_step_for_large_orders: Optional[bool] = None
    large_order_threshold_usd: Optional[float] = Field(default=None, ge=0)


# ---------- Audit ----------

class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    raw_command: Optional[str]
    parsed_payload: Optional[dict[str, Any]]
    result_payload: Optional[dict[str, Any]]
    success: bool
    message: Optional[str]
    created_at: datetime
