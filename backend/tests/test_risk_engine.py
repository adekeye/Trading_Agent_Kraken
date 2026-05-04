"""Unit tests for the risk engine."""
import pytest

from app.command_parser import parse_command
from app.models import UserSettings
from app.risk_engine import RiskEngine
from app.schemas import ParsedCommand


def make_settings(**overrides) -> UserSettings:
    s = UserSettings()
    s.dry_run = overrides.get("dry_run", True)
    s.trading_enabled = overrides.get("trading_enabled", True)
    s.max_order_notional_usd = overrides.get("max_order_notional_usd", 1000.0)
    s.preferred_quote_currency = overrides.get("preferred_quote_currency", "USD")
    s.require_two_step_for_large_orders = overrides.get("require_two_step_for_large_orders", True)
    s.large_order_threshold_usd = overrides.get("large_order_threshold_usd", 5000.0)
    return s


@pytest.mark.asyncio
async def test_approves_clean_buy():
    parsed = parse_command("Buy 100 XRP at 0.50")  # notional 50
    decision = await RiskEngine(make_settings()).evaluate(parsed)
    assert decision.approved is True
    assert decision.reason is None


@pytest.mark.asyncio
async def test_kill_switch_blocks_orders():
    parsed = parse_command("Buy 100 XRP at 0.50")
    decision = await RiskEngine(make_settings(trading_enabled=False)).evaluate(parsed)
    assert decision.approved is False
    assert "kill" in (decision.reason or "").lower() or "disabled" in (decision.reason or "").lower()


@pytest.mark.asyncio
async def test_max_order_size_enforced():
    parsed = parse_command("Buy 1000 XRP at 0.55")  # notional 550
    decision = await RiskEngine(make_settings(max_order_notional_usd=500)).evaluate(parsed)
    assert decision.approved is False
    assert "max order size" in (decision.reason or "").lower()


@pytest.mark.asyncio
async def test_two_step_required_for_large_orders():
    parsed = parse_command("Buy 1000 XRP at 0.55")  # notional 550
    decision = await RiskEngine(
        make_settings(max_order_notional_usd=10_000, large_order_threshold_usd=500)
    ).evaluate(parsed)
    assert decision.approved is True
    assert decision.requires_two_step is True


@pytest.mark.asyncio
async def test_unsupported_asset_rejected_by_parser_then_engine():
    parsed = parse_command("Buy 5 DOGEFAKE at 0.10")
    # parser rejects unknown asset
    assert parsed.rejection_reason is not None
    decision = await RiskEngine(make_settings()).evaluate(parsed)
    assert decision.approved is False


@pytest.mark.asyncio
async def test_reject_rejection_reason_propagates():
    parsed = parse_command("Market buy BTC")
    decision = await RiskEngine(make_settings()).evaluate(parsed)
    assert decision.approved is False
    assert decision.reason is not None


@pytest.mark.asyncio
async def test_show_balances_intent_passes_without_trading_check():
    parsed = parse_command("show my balances")
    decision = await RiskEngine(make_settings(trading_enabled=False)).evaluate(parsed)
    assert decision.approved is True


@pytest.mark.asyncio
async def test_negative_quantity_blocked():
    parsed = ParsedCommand(
        intent="place_order", side="buy", asset="BTC", quote_currency="USD",
        quantity=-1, limit_price=100, order_type="limit",
        confidence=0.9, requires_confirmation=True,
    )
    decision = await RiskEngine(make_settings()).evaluate(parsed)
    assert decision.approved is False


@pytest.mark.asyncio
async def test_zero_price_blocked():
    parsed = ParsedCommand(
        intent="place_order", side="buy", asset="BTC", quote_currency="USD",
        quantity=1, limit_price=0, order_type="limit",
        confidence=0.9, requires_confirmation=True,
    )
    decision = await RiskEngine(make_settings()).evaluate(parsed)
    assert decision.approved is False


@pytest.mark.asyncio
async def test_stop_loss_limit_approved():
    parsed = parse_command("Sell 0.01 BTC stop loss at 60000 limit 59500")
    decision = await RiskEngine(
        make_settings(max_order_notional_usd=10_000)
    ).evaluate(parsed)
    assert decision.approved is True


@pytest.mark.asyncio
async def test_stop_loss_limit_without_trigger_blocked():
    """Risk engine catches a stop-loss-limit with a missing trigger."""
    parsed = ParsedCommand(
        intent="place_order", side="sell", asset="BTC", quote_currency="USD",
        quantity=1, limit_price=59500, trigger_price=None,
        order_type="stop-loss-limit",
        confidence=0.9, requires_confirmation=True,
    )
    decision = await RiskEngine(make_settings(max_order_notional_usd=200_000)).evaluate(parsed)
    assert decision.approved is False
    assert "trigger" in (decision.reason or "").lower()


@pytest.mark.asyncio
async def test_unknown_order_type_blocked():
    parsed = ParsedCommand(
        intent="place_order", side="sell", asset="BTC", quote_currency="USD",
        quantity=1, limit_price=100, order_type="limit",  # type-checker
        confidence=0.9, requires_confirmation=True,
    )
    # bypass typing to simulate a future/unsupported type
    parsed.order_type = "trailing-stop"  # type: ignore
    decision = await RiskEngine(make_settings()).evaluate(parsed)
    assert decision.approved is False
