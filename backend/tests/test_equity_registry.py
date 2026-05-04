"""Tests for the dynamic xStocks equity registry."""
import httpx
import pytest
import respx

from app.equities import (
    EquityRegistry,
    FALLBACK_EQUITY_TICKERS,
    _filter_xstocks_from_asset_pairs,
    get_registry,
)
from app.kraken_client import KrakenClient


# A realistic-looking subset of Kraken's /AssetPairs response: a mix of crypto
# pairs (XBTUSD, XRPUSD, ETHUSD), tokenized equities (AAPLXUSD, TSLAXUSD,
# NVDAXUSD, SPYXUSD), and a couple of edge cases we want the filter to skip.
_FAKE_ASSET_PAIRS = {
    "XXBTZUSD": {"altname": "XBTUSD", "wsname": "XBT/USD", "base": "XXBT", "quote": "ZUSD"},
    "XETHZUSD": {"altname": "ETHUSD", "wsname": "ETH/USD", "base": "XETH", "quote": "ZUSD"},
    "XRPUSD":   {"altname": "XRPUSD", "wsname": "XRP/USD", "base": "XRP",  "quote": "ZUSD"},
    "AAPLXUSD": {"altname": "AAPLXUSD", "wsname": "AAPLX/USD", "base": "AAPLX", "quote": "ZUSD"},
    "TSLAXUSD": {"altname": "TSLAXUSD", "wsname": "TSLAX/USD", "base": "TSLAX", "quote": "ZUSD"},
    "NVDAXUSD": {"altname": "NVDAXUSD", "wsname": "NVDAX/USD", "base": "NVDAX", "quote": "ZUSD"},
    "SPYXUSD":  {"altname": "SPYXUSD",  "wsname": "SPYX/USD",  "base": "SPYX",  "quote": "ZUSD"},
    "GOOGLXUSD": {"altname": "GOOGLXUSD", "wsname": "GOOGLX/USD", "base": "GOOGLX", "quote": "ZUSD"},
    # Only-USDT quote — should still match
    "BRKXUSDT": {"altname": "BRKXUSDT", "wsname": "BRKX/USDT", "base": "BRKX", "quote": "USDT"},
    # Edge: tiny base that ends in X but is too short to be a real ticker
    "XX":       {"altname": "XX", "base": "XX", "quote": "ZUSD"},
    # Edge: legacy crypto base prefixed with X
    "XLTCZUSD": {"altname": "LTCUSD", "base": "XLTC", "quote": "ZUSD"},
}


def _kraken_response(result, error=None):
    return {"error": error or [], "result": result}


def test_filter_extracts_xstocks_only():
    discovered = _filter_xstocks_from_asset_pairs(_FAKE_ASSET_PAIRS)
    # All five xStocks recognized
    assert {"AAPL", "TSLA", "NVDA", "SPY", "GOOGL", "BRK"} <= discovered
    # Crypto pairs and bad bases are NOT in the result
    assert "XBT" not in discovered
    assert "XXBT" not in discovered
    assert "XRP" not in discovered
    assert "XETH" not in discovered
    assert "XLTC" not in discovered
    # XX is too short
    assert "X" not in discovered


def test_filter_handles_empty_response():
    assert _filter_xstocks_from_asset_pairs({}) == set()


def test_filter_skips_pairs_with_unknown_quote():
    # A pair quoted in some unknown currency should be ignored.
    pairs = {"XYZUSD": {"base": "XYZX", "quote": "GBP"}}  # GBP not in our set
    assert _filter_xstocks_from_asset_pairs(pairs) == set()


@pytest.mark.asyncio
@respx.mock
async def test_registry_refresh_populates_from_kraken():
    respx.get("https://api.kraken.com/0/public/AssetPairs").mock(
        return_value=httpx.Response(200, json=_kraken_response(_FAKE_ASSET_PAIRS))
    )
    registry = EquityRegistry()
    async with KrakenClient() as kc:
        st = await registry.refresh(kc)
    assert st.last_error is None
    assert st.using_fallback is False
    assert "AAPL" in registry.tickers()
    assert "BRK" in registry.tickers()
    # Union with fallback also still serves any curated tickers
    assert FALLBACK_EQUITY_TICKERS <= registry.tickers()


@pytest.mark.asyncio
@respx.mock
async def test_registry_refresh_falls_back_on_error():
    respx.get("https://api.kraken.com/0/public/AssetPairs").mock(
        return_value=httpx.Response(500, json={"error": ["EService:Unavailable"]})
    )
    registry = EquityRegistry()
    async with KrakenClient() as kc:
        st = await registry.refresh(kc)
    # Refresh failed, but fallback list is still served
    assert st.last_error is not None
    assert st.using_fallback is True
    assert FALLBACK_EQUITY_TICKERS <= registry.tickers()


def test_registry_serves_fallback_when_unrefreshed():
    registry = EquityRegistry()
    assert registry.tickers() == FALLBACK_EQUITY_TICKERS
    assert registry.is_supported("AAPL")
    assert registry.is_supported("TSLA")
    assert not registry.is_supported("ZZZ-not-a-real-ticker")


def test_registry_status_initial_state():
    registry = EquityRegistry()
    s = registry.status()
    assert s.fetched_at is None
    assert s.using_fallback is True
    assert s.last_error is None
    assert s.ticker_count == len(FALLBACK_EQUITY_TICKERS)


def test_get_registry_returns_singleton():
    a = get_registry()
    b = get_registry()
    assert a is b
