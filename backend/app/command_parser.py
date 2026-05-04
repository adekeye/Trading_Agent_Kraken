"""Deterministic, structured natural-language parser for trading commands.

Design goals:
- Be safe and explicit. Reject ambiguity.
- Use rule-based extraction first; an LLM hook is provided but not enabled by default.
- Return a `ParsedCommand` schema with high-confidence rejections rather than guesses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .equities import (
    EQUITY_ALIASES,
    EQUITY_DISCLOSURE,
    get_registry,
    normalize_equity_ticker,
)
from .schemas import ParsedCommand


# ---------- Lexicons ----------

SUPPORTED_CRYPTO_ASSETS = {
    "BTC", "BITCOIN", "XBT",
    "ETH", "ETHEREUM",
    "XRP", "RIPPLE",
    "SOL", "SOLANA",
    "ADA", "DOT", "DOGE",
    "USDT", "USDC",
    "MATIC", "LINK",
}


def _supported_assets() -> set[str]:
    """All recognisable asset tokens (crypto + dynamically-discovered xStocks
    + natural-language aliases). Computed per-call so the equity registry
    can update without a process restart."""
    return (
        SUPPORTED_CRYPTO_ASSETS
        | get_registry().tickers()
        | {alias.upper() for alias in EQUITY_ALIASES}
    )

QUOTE_CURRENCIES = {"USD", "USDT", "USDC", "EUR", "GBP"}

VAGUE_PHRASES = {
    "go all in", "all in", "make me money", "trade for me", "trade for me automatically",
    "buy whatever is pumping", "sell if it looks bad", "sell all crypto",
    "yolo", "moon", "pump", "auto trade", "auto-trade",
}

INTENT_KEYWORDS = {
    "show_balances": [
        "show my balances", "show balances", "balance", "balances", "my balance",
        "account balance", "kraken balance",
    ],
    "show_orders": [
        "show open orders", "show my open orders", "open orders", "list orders",
        "what orders", "current orders",
    ],
    "show_history": [
        "show order history", "order history", "recent orders", "closed orders",
        "trade history",
    ],
}

CANCEL_PATTERN = re.compile(
    # Real Kraken txids contain at least one digit (e.g. "OABC123", "OXYZ-AAA-1B2").
    # The lookahead enforces that, so words like "open" don't get captured as a txid.
    r"\bcancel\s+(?:my\s+)?(?:order\s+)?(?:#)?(?P<txid>(?=[A-Za-z0-9\-]*\d)[A-Za-z0-9\-]{4,})\b",
    re.IGNORECASE,
)

CANCEL_GENERIC = re.compile(
    r"\bcancel(?:\s+my)?\s+(?:open\s+)?(?P<asset>[a-z]{2,8})?\s*order\b",
    re.IGNORECASE,
)


# ---------- Helpers ----------

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"


@dataclass
class _Extracted:
    side: str | None = None
    asset: str | None = None
    quote_currency: str | None = None
    quantity: float | None = None
    notional_amount: float | None = None
    limit_price: float | None = None
    order_type: str | None = None
    rejection: str | None = None
    confidence: float = 0.0


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def _detect_side(text: str) -> str | None:
    if re.search(r"\bbuy\b", text):
        return "buy"
    if re.search(r"\bsell\b", text):
        return "sell"
    return None


_CRYPTO_ALIASES = {
    "BITCOIN": "BTC",
    "XBT": "BTC",
    "ETHEREUM": "ETH",
    "RIPPLE": "XRP",
    "SOLANA": "SOL",
}


def _detect_asset(text: str) -> tuple[str | None, str | None]:
    """Return ``(canonical_symbol, asset_class)`` where asset_class is
    ``"crypto"`` or ``"equity"``. Match longest-first so multi-word aliases
    like ``"bitcoin"`` win over ``"btc"`` when both are present."""
    words = sorted(_supported_assets(), key=len, reverse=True)
    for w in words:
        if re.search(rf"\b{re.escape(w.lower())}\b", text):
            equity = normalize_equity_ticker(w)
            if equity is not None:
                return equity, "equity"
            return _CRYPTO_ALIASES.get(w.upper(), w.upper()), "crypto"
    return None, None


def _detect_quote(text: str) -> str | None:
    for q in QUOTE_CURRENCIES:
        if re.search(rf"\b{q.lower()}\b", text):
            return q
    if "$" in text:
        return "USD"
    if "€" in text:
        return "EUR"
    if "£" in text:
        return "GBP"
    return None


def _detect_order_type(text: str) -> tuple[str | None, str | None]:
    """Returns (order_type, rejection_reason)."""
    if re.search(r"\bmarket\s+(buy|sell)\b|\bmarket\s+order\b", text):
        return None, "Rejected: only limit orders are supported. Specify a limit price."
    if re.search(r"\bstop[-\s]?loss\b|\bstop\b\s+order|\btrailing\b", text):
        return None, "Rejected: only limit orders are supported."
    if re.search(r"\b(at|@|limit)\b", text):
        return "limit", None
    # 'if price reaches X' is treated as a stop trigger we don't support
    if re.search(r"\bif\s+price\s+reaches\b|\bwhen\s+price\s+hits\b", text):
        return None, "Rejected: conditional/stop orders are not supported. Use a plain limit price (e.g. 'buy 1 ETH at 3100')."
    return None, None


def _detect_quantity_and_notional(text: str) -> tuple[float | None, float | None]:
    """Find an explicit quantity (e.g. '1000 xrp', '0.05 btc') and/or notional ($1000)."""
    quantity = None
    notional = None

    # $X worth of / $X of  → notional
    m = re.search(rf"\$?\s*({_NUM})\s*(?:dollars|usd|eur|gbp)?\s*(?:worth\s+of|of)\s+", text)
    if m and "$" in text or (m and re.search(r"worth", text)):
        try:
            notional = _to_float(m.group(1))
        except ValueError:
            pass

    # straightforward "$1000" alone (without "worth of") still implies notional if no qty present
    m_dollar = re.search(rf"\$\s*({_NUM})", text)
    if m_dollar and notional is None:
        try:
            notional = _to_float(m_dollar.group(1))
        except ValueError:
            pass

    # quantity-then-asset: "1000 xrp", "0.05 btc"
    asset_alt = "|".join(sorted({a.lower() for a in _supported_assets()}, key=len, reverse=True))
    m_qty = re.search(rf"({_NUM})\s+(?:units?\s+of\s+)?({asset_alt})\b", text)
    if m_qty:
        try:
            quantity = _to_float(m_qty.group(1))
        except ValueError:
            pass

    return quantity, notional


def _detect_limit_price(text: str) -> float | None:
    # "at 0.55", "@ 65000", "at $3,100", "limit price of 3100"
    # Note: \b doesn't anchor at '@' (non-word char), so we use a non-word-boundary
    # alternative for that branch.
    patterns = [
        rf"(?:\bat\b|@)\s*\$?\s*({_NUM})",
        rf"\blimit\s+price\s+(?:of\s+)?\$?\s*({_NUM})",
        rf"\bfor\s+\$?\s*({_NUM})\s+each\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return _to_float(m.group(1))
            except ValueError:
                continue
    return None


# ---------- Public API ----------

def parse_command(raw: str) -> ParsedCommand:
    """Parse a natural-language command into a ParsedCommand schema."""
    if raw is None or not raw.strip():
        return ParsedCommand(
            intent="unknown",
            confidence=0.0,
            requires_confirmation=False,
            rejection_reason="Empty command.",
        )

    text = _normalize(raw)

    # --- Hard rejections (before anything else) ---
    # Note: equities are now supported via Kraken's xStocks (tokenized stocks).
    # We no longer reject the words "stock"/"shares"; instead we let the
    # ticker-detection step decide. If someone types "buy IBM at 200" but IBM
    # is not in our xStocks allowlist, the asset-detection branch below will
    # produce a precise "unsupported asset" rejection instead of a blanket
    # "stocks not supported" message.
    for phrase in VAGUE_PHRASES:
        if phrase in text:
            return ParsedCommand(
                intent="unknown",
                confidence=0.9,
                requires_confirmation=False,
                rejection_reason=(
                    f"Rejected: command is too vague ('{phrase}'). "
                    "Please specify side, asset, quantity, and a limit price."
                ),
            )

    # --- Read-only intents ---
    for intent, phrases in INTENT_KEYWORDS.items():
        for phrase in phrases:
            if phrase in text:
                return ParsedCommand(
                    intent=intent,  # type: ignore[arg-type]
                    confidence=0.95,
                    requires_confirmation=False,
                )

    # --- Cancel order ---
    m_cancel = CANCEL_PATTERN.search(raw)
    if m_cancel:
        return ParsedCommand(
            intent="cancel_order",
            confidence=0.95,
            requires_confirmation=True,
            cancel_txid=m_cancel.group("txid"),
        )
    if "cancel" in text:
        m2 = CANCEL_GENERIC.search(text)
        if m2:
            return ParsedCommand(
                intent="cancel_order",
                confidence=0.4,
                requires_confirmation=False,
                rejection_reason=(
                    "Rejected: please specify the order id to cancel "
                    "(e.g. 'cancel order OABC123')."
                ),
            )

    # --- Place order intent ---
    side = _detect_side(text)
    if side is None:
        return ParsedCommand(
            intent="unknown",
            confidence=0.2,
            requires_confirmation=False,
            rejection_reason=(
                "Rejected: command did not match any supported intent. "
                "Try 'buy 100 XRP at 0.55' or 'show balances'."
            ),
        )

    order_type, otype_reject = _detect_order_type(text)
    if otype_reject:
        return ParsedCommand(
            intent="place_order",
            confidence=0.9,
            side=side,
            requires_confirmation=False,
            rejection_reason=otype_reject,
        )

    asset, asset_class = _detect_asset(text)
    if asset is None:
        equity_tickers = sorted(get_registry().tickers())
        # Cap the displayed list so rejection messages don't get huge once
        # discovery brings in 50+ tickers.
        equity_preview = ", ".join(equity_tickers[:25])
        if len(equity_tickers) > 25:
            equity_preview += f", … (+{len(equity_tickers) - 25} more)"
        return ParsedCommand(
            intent="place_order",
            confidence=0.4,
            side=side,
            requires_confirmation=False,
            rejection_reason=(
                "Rejected: unsupported or missing asset. "
                "Supported crypto: BTC, ETH, XRP, SOL, ADA, DOT, DOGE, USDT, USDC, MATIC, LINK. "
                f"Supported equities (xStocks): {equity_preview}."
            ),
        )

    quote = _detect_quote(text) or "USD"
    quantity, notional = _detect_quantity_and_notional(text)
    limit_price = _detect_limit_price(text)

    # 'sell all my eth at 4000' style — explicitly reject (we require numeric quantity)
    if re.search(r"\b(all|everything|all\s+my|max|maximum)\b", text) and quantity is None:
        return ParsedCommand(
            intent="place_order",
            confidence=0.7,
            side=side,
            asset=asset,
            quote_currency=quote,
            requires_confirmation=False,
            rejection_reason=(
                "Rejected: quantity 'all' is not allowed. Specify an exact amount "
                "(e.g. 'sell 0.5 ETH at 4000')."
            ),
        )

    if limit_price is None:
        return ParsedCommand(
            intent="place_order",
            confidence=0.6,
            side=side,
            asset=asset,
            quote_currency=quote,
            quantity=quantity,
            notional_amount=notional,
            requires_confirmation=False,
            rejection_reason="Rejected: limit price is missing. Add 'at <price>'.",
        )

    if quantity is None and notional is None:
        return ParsedCommand(
            intent="place_order",
            confidence=0.5,
            side=side,
            asset=asset,
            quote_currency=quote,
            limit_price=limit_price,
            requires_confirmation=False,
            rejection_reason="Rejected: quantity is missing. Specify an exact amount or a $ notional.",
        )

    # Derive quantity from notional if needed.
    warnings: list[str] = []
    if quantity is None and notional is not None:
        quantity = round(notional / limit_price, 8)
        warnings.append(
            f"Quantity {quantity} derived from notional {notional} {quote} at {limit_price}"
        )

    # Surface tokenized-equity disclosure on every equity order so the user
    # confirms with eyes open.
    if asset_class == "equity":
        warnings.append(EQUITY_DISCLOSURE)

    # Confidence scoring: more explicit = higher
    confidence = 0.6
    if quantity and limit_price and asset and side:
        confidence = 0.9
    if notional is not None:
        confidence = min(confidence, 0.85)

    return ParsedCommand(
        intent="place_order",
        side=side,
        asset=asset,
        quote_currency=quote,
        quantity=quantity,
        notional_amount=notional,
        limit_price=limit_price,
        order_type="limit",
        confidence=confidence,
        requires_confirmation=True,
        warnings=warnings,
    )
