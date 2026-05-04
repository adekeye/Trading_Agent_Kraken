"""Unit tests for the natural-language command parser."""
import pytest

from app.command_parser import parse_command


# ---------- Happy path: place_order ----------

def test_buy_with_quantity_and_limit_price():
    p = parse_command("Buy 1000 XRP at 0.55")
    assert p.intent == "place_order"
    assert p.side == "buy"
    assert p.asset == "XRP"
    assert p.quantity == 1000
    assert p.limit_price == 0.55
    assert p.order_type == "limit"
    assert p.rejection_reason is None
    assert p.requires_confirmation is True


def test_sell_btc_decimal_quantity():
    p = parse_command("sell 0.05 btc at 65000")
    assert p.intent == "place_order"
    assert p.side == "sell"
    assert p.asset == "BTC"
    assert p.quantity == 0.05
    assert p.limit_price == 65000


def test_buy_with_dollar_notional_derives_quantity():
    p = parse_command("Buy $500 worth of ETH at 3100")
    assert p.intent == "place_order"
    assert p.side == "buy"
    assert p.asset == "ETH"
    assert p.notional_amount == 500
    assert p.limit_price == 3100
    # quantity derived: 500 / 3100 ≈ 0.16129
    assert p.quantity is not None
    assert abs(p.quantity - (500 / 3100)) < 1e-6
    assert any("derived from notional" in w for w in p.warnings)


def test_bitcoin_alias_maps_to_btc():
    p = parse_command("buy 0.1 bitcoin at 60000")
    assert p.asset == "BTC"
    assert p.quantity == 0.1


def test_thousands_separator_in_price():
    p = parse_command("sell 2 ETH at $4,200")
    assert p.intent == "place_order"
    assert p.limit_price == 4200
    assert p.quantity == 2


def test_alternative_at_symbol():
    p = parse_command("buy 100 sol @ 150")
    assert p.intent == "place_order"
    assert p.limit_price == 150


# ---------- Rejections ----------

def test_bare_tesla_still_rejected_for_missing_qty_and_price():
    """We accept equity tickers, but a bare 'Buy Tesla stock' is still
    incomplete — no quantity, no limit price. The rejection is now about
    the missing fields, not about stocks being unsupported."""
    p = parse_command("Buy Tesla stock")
    assert p.intent == "place_order"
    assert p.asset == "TSLA"
    assert p.rejection_reason is not None
    # Should NOT reject for being a stock anymore.
    reason = (p.rejection_reason or "").lower()
    assert "limit price" in reason or "quantity" in reason


def test_apple_shares_with_qty_and_price_accepted():
    """'Buy 10 Apple shares at 200' was previously rejected; now it
    parses to AAPL with the equity disclosure attached."""
    p = parse_command("Buy 10 Apple shares at 200")
    assert p.intent == "place_order"
    assert p.side == "buy"
    assert p.asset == "AAPL"
    assert p.quantity == 10
    assert p.limit_price == 200
    assert p.rejection_reason is None
    assert any("xstocks" in w.lower() or "tokenized" in w.lower() for w in p.warnings)


def test_tesla_ticker_aliased_to_tsla():
    p = parse_command("Sell 2 TSLA at 250")
    assert p.intent == "place_order"
    assert p.asset == "TSLA"
    assert p.quantity == 2
    assert p.limit_price == 250


def test_unknown_ticker_rejected_with_helpful_message():
    p = parse_command("Buy 10 IBM at 200")
    # IBM is not in our xStocks allowlist (yet) — should reject precisely.
    assert p.rejection_reason is not None
    reason = (p.rejection_reason or "").lower()
    assert "unsupported" in reason or "missing asset" in reason


def test_rejects_market_order():
    p = parse_command("Market buy BTC")
    assert p.rejection_reason is not None
    assert "limit" in p.rejection_reason.lower()


def test_rejects_missing_price():
    p = parse_command("Buy BTC")
    assert p.rejection_reason is not None


def test_rejects_missing_asset():
    p = parse_command("buy 100 at 50")
    assert p.rejection_reason is not None


def test_rejects_vague_all_in():
    p = parse_command("go all in on bitcoin")
    assert p.intent == "unknown"
    assert p.rejection_reason is not None


def test_rejects_make_me_money():
    p = parse_command("make me money")
    assert p.intent == "unknown"


def test_rejects_sell_all_keyword():
    p = parse_command("Sell all my eth at 4000")
    assert p.rejection_reason is not None
    assert "all" in p.rejection_reason.lower()


def test_conditional_take_profit_accepted():
    """'if price reaches X' (rises) → take-profit-limit. Trigger and limit both 180."""
    p = parse_command("Sell 100 SOL if price rises to 180")
    assert p.intent == "place_order"
    assert p.rejection_reason is None
    assert p.order_type == "take-profit-limit"
    assert p.trigger_price == 180
    assert p.limit_price == 180
    # Slippage warning when trigger == limit
    assert any("trigger price equals limit" in w.lower() for w in p.warnings)


def test_conditional_stop_loss_accepted():
    """'if price falls to X' → stop-loss-limit."""
    p = parse_command("Sell 100 SOL if price falls to 150")
    assert p.intent == "place_order"
    assert p.order_type == "stop-loss-limit"
    assert p.trigger_price == 150
    assert p.limit_price == 150


def test_explicit_stop_loss_with_separate_limit():
    """User supplies separate trigger and limit prices."""
    p = parse_command("Sell 100 SOL stop loss at 180 limit 175")
    assert p.intent == "place_order"
    assert p.order_type == "stop-loss-limit"
    assert p.trigger_price == 180
    assert p.limit_price == 175
    assert p.rejection_reason is None


def test_take_profit_phrase_accepted():
    p = parse_command("Sell 2 ETH take profit at 4500 limit 4490")
    assert p.intent == "place_order"
    assert p.order_type == "take-profit-limit"
    assert p.trigger_price == 4500
    assert p.limit_price == 4490


def test_when_price_hits_defaults_to_stop_loss_for_safety():
    """The ambiguous word 'hits' defaults to stop-loss (safer)."""
    p = parse_command("Sell 1 BTC when price hits 60000")
    assert p.intent == "place_order"
    assert p.order_type == "stop-loss-limit"
    assert p.trigger_price == 60000


def test_rejects_market_stop_loss():
    """Bare 'stop loss' (without -limit) on Kraken becomes a stop-loss-MARKET,
    which we deliberately don't support. We require an explicit limit price."""
    p = parse_command("Sell 1 BTC stop loss at 60000")
    # Stop loss with single price → trigger = 60000, limit defaults to 60000 (still a limit-backed order). Accepted.
    assert p.intent == "place_order"
    assert p.order_type == "stop-loss-limit"
    assert p.rejection_reason is None


# ---------- Read-only intents ----------

def test_show_balances():
    p = parse_command("Show my balances")
    assert p.intent == "show_balances"
    assert p.requires_confirmation is False


def test_show_open_orders():
    p = parse_command("Show open orders")
    assert p.intent == "show_orders"


def test_cancel_with_txid():
    p = parse_command("Cancel order OABC123")
    assert p.intent == "cancel_order"
    assert p.cancel_txid is not None


def test_cancel_generic_without_txid_rejected():
    p = parse_command("Cancel my open BTC order")
    assert p.intent == "cancel_order"
    # We only cancel by txid; generic cancel must be rejected
    assert p.rejection_reason is not None


def test_empty_input():
    p = parse_command("   ")
    assert p.intent == "unknown"
    assert p.rejection_reason is not None
