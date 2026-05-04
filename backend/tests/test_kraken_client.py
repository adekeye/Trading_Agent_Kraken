"""Mock-based integration tests for the Kraken client and order flow."""
import base64
import os

import httpx
import pytest
import respx

from app.kraken_client import KrakenAPIError, KrakenClient, to_kraken_pair_altname


# A valid base64-encoded "secret" for signing math (32 bytes -> base64).
TEST_SECRET = base64.b64encode(b"\0" * 32).decode()


def _kraken_response(result, error=None):
    return {"error": error or [], "result": result}


@pytest.mark.asyncio
async def test_to_kraken_pair_altname_normalizes_btc():
    assert to_kraken_pair_altname("BTC", "USD") == "XBTUSD"
    assert to_kraken_pair_altname("bitcoin", "usd") == "XBTUSD"
    assert to_kraken_pair_altname("XRP", "USD") == "XRPUSD"


@pytest.mark.asyncio
@respx.mock
async def test_balance_signs_and_returns_data():
    route = respx.post("https://api.kraken.com/0/private/Balance").mock(
        return_value=httpx.Response(200, json=_kraken_response({"ZUSD": "100.00", "XXBT": "0.5"}))
    )
    async with KrakenClient(api_key="key", api_secret=TEST_SECRET) as kc:
        result = await kc.balance()
    assert route.called
    assert result == {"ZUSD": "100.00", "XXBT": "0.5"}
    # Required headers are present
    req = route.calls.last.request
    assert req.headers.get("API-Key") == "key"
    assert req.headers.get("API-Sign")  # signature populated


@pytest.mark.asyncio
@respx.mock
async def test_kraken_error_raises():
    respx.post("https://api.kraken.com/0/private/Balance").mock(
        return_value=httpx.Response(200, json=_kraken_response(None, error=["EAPI:Invalid key"]))
    )
    async with KrakenClient(api_key="key", api_secret=TEST_SECRET) as kc:
        with pytest.raises(KrakenAPIError):
            await kc.balance()


@pytest.mark.asyncio
@respx.mock
async def test_add_order_only_supports_limit():
    async with KrakenClient(api_key="key", api_secret=TEST_SECRET) as kc:
        with pytest.raises(ValueError):
            await kc.add_order(pair="XBTUSD", side="buy", ordertype="market", volume=1, price=1)


@pytest.mark.asyncio
@respx.mock
async def test_add_order_happy_path_returns_txid():
    expected = {
        "descr": {"order": "buy 1.00000000 XBTUSD @ limit 65000.0"},
        "txid": ["O7XYZ-AAA-BBB"],
    }
    route = respx.post("https://api.kraken.com/0/private/AddOrder").mock(
        return_value=httpx.Response(200, json=_kraken_response(expected))
    )
    async with KrakenClient(api_key="key", api_secret=TEST_SECRET) as kc:
        result = await kc.add_order(
            pair="XBTUSD", side="buy", ordertype="limit", volume="1", price="65000"
        )
    assert route.called
    assert result["txid"] == ["O7XYZ-AAA-BBB"]
    sent = route.calls.last.request
    assert b"pair=XBTUSD" in sent.content
    assert b"type=buy" in sent.content
    assert b"ordertype=limit" in sent.content


@pytest.mark.asyncio
@respx.mock
async def test_cancel_order_called_with_txid():
    route = respx.post("https://api.kraken.com/0/private/CancelOrder").mock(
        return_value=httpx.Response(200, json=_kraken_response({"count": 1}))
    )
    async with KrakenClient(api_key="key", api_secret=TEST_SECRET) as kc:
        result = await kc.cancel_order("OABC-123")
    assert route.called
    assert result == {"count": 1}
    assert b"txid=OABC-123" in route.calls.last.request.content


@pytest.mark.asyncio
@respx.mock
async def test_open_orders_returns_dict():
    payload = {"open": {"OXYZ-1": {"descr": {"pair": "XBTUSD", "type": "buy", "ordertype": "limit", "price": "65000"}, "vol": "0.1", "status": "open", "opentm": 1700000000.0}}}
    respx.post("https://api.kraken.com/0/private/OpenOrders").mock(
        return_value=httpx.Response(200, json=_kraken_response(payload))
    )
    async with KrakenClient(api_key="key", api_secret=TEST_SECRET) as kc:
        result = await kc.open_orders()
    assert "open" in result
    assert "OXYZ-1" in result["open"]
