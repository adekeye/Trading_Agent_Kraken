"""Risk engine: validates a parsed command against per-user safety rules."""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import UserSettings
from .schemas import ParsedCommand


from .equities import get_registry

SUPPORTED_CRYPTO_ASSETS = {
    "BTC", "ETH", "XRP", "SOL", "ADA", "DOT", "DOGE", "USDT", "USDC", "MATIC", "LINK",
}


def _supported_assets() -> set[str]:
    """Crypto symbols + xStocks (tokenized equity) tickers, evaluated lazily so
    the registry can refresh without restarting the process."""
    return SUPPORTED_CRYPTO_ASSETS | get_registry().tickers()


SUPPORTED_QUOTES = {"USD", "USDT", "USDC", "EUR", "GBP"}


@dataclass
class RiskDecision:
    approved: bool
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    requires_two_step: bool = False


class RiskEngine:
    def __init__(self, settings: UserSettings) -> None:
        self.s = settings

    async def evaluate(self, parsed: ParsedCommand) -> RiskDecision:
        # Read-only intents bypass trading-specific rules
        if parsed.intent in {"show_balances", "show_orders", "show_history"}:
            return RiskDecision(approved=True)

        if parsed.intent == "cancel_order":
            if not parsed.cancel_txid:
                return RiskDecision(approved=False, reason="Cancel intent missing order id.")
            return RiskDecision(approved=True)

        # Anything other than place_order at this point: reject
        if parsed.intent != "place_order":
            return RiskDecision(
                approved=False,
                reason=parsed.rejection_reason or "Unrecognized intent.",
            )

        # Bubble up parser-level rejections
        if parsed.rejection_reason:
            return RiskDecision(approved=False, reason=parsed.rejection_reason)

        # Global kill switch
        if not self.s.trading_enabled:
            return RiskDecision(
                approved=False,
                reason="Trading is currently disabled (kill switch). Re-enable in Settings.",
            )

        # Side must be present
        if parsed.side not in {"buy", "sell"}:
            return RiskDecision(approved=False, reason="Order side must be 'buy' or 'sell'.")

        # Asset/quote support
        if parsed.asset is None or parsed.asset.upper() not in _supported_assets():
            return RiskDecision(
                approved=False,
                reason=f"Asset '{parsed.asset}' is not in the supported asset list.",
            )
        quote = (parsed.quote_currency or self.s.preferred_quote_currency or "USD").upper()
        if quote not in SUPPORTED_QUOTES:
            return RiskDecision(
                approved=False,
                reason=f"Quote currency '{quote}' is not supported.",
            )

        # Order type — accept plain limit and the two limit-backed conditional
        # variants. Market / stop-loss-MARKET / trailing are still rejected.
        SUPPORTED_ORDER_TYPES = {"limit", "stop-loss-limit", "take-profit-limit"}
        if parsed.order_type and parsed.order_type not in SUPPORTED_ORDER_TYPES:
            return RiskDecision(
                approved=False,
                reason=(
                    f"Order type '{parsed.order_type}' is not supported. "
                    f"Allowed: {', '.join(sorted(SUPPORTED_ORDER_TYPES))}."
                ),
            )

        # Numeric sanity
        if parsed.quantity is None or parsed.quantity <= 0:
            return RiskDecision(approved=False, reason="Quantity must be positive.")
        if parsed.limit_price is None or parsed.limit_price <= 0:
            return RiskDecision(approved=False, reason="Limit price must be positive.")

        # Conditional orders need a trigger and it must be positive.
        is_conditional = parsed.order_type in {"stop-loss-limit", "take-profit-limit"}
        if is_conditional:
            if parsed.trigger_price is None or parsed.trigger_price <= 0:
                return RiskDecision(approved=False, reason="Trigger price must be positive.")

        notional = parsed.quantity * parsed.limit_price
        if notional > self.s.max_order_notional_usd:
            return RiskDecision(
                approved=False,
                reason=(
                    f"Order exceeds your configured max order size of "
                    f"{self.s.max_order_notional_usd:.2f} {self.s.preferred_quote_currency} "
                    f"(this order: {notional:.2f})."
                ),
            )

        # Confidence floor (we still warn even if accepted)
        warnings: list[str] = list(parsed.warnings or [])
        if parsed.confidence < 0.7:
            warnings.append(
                f"Parser confidence is low ({parsed.confidence:.2f}); review the preview carefully."
            )

        requires_two_step = (
            self.s.require_two_step_for_large_orders
            and notional >= self.s.large_order_threshold_usd
        )
        if requires_two_step:
            warnings.append(
                f"This order ({notional:.2f}) is at or above your large-order threshold "
                f"({self.s.large_order_threshold_usd:.2f}); a two-step confirmation phrase is required."
            )

        return RiskDecision(
            approved=True,
            warnings=warnings,
            requires_two_step=requires_two_step,
        )
