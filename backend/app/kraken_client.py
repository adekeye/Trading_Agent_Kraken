"""Minimal async Kraken REST client.

Implements only the endpoints this app needs:
- Public:  /0/public/AssetPairs
- Private: /0/private/Balance, /0/private/AddOrder, /0/private/OpenOrders,
           /0/private/CancelOrder, /0/private/ClosedOrders

Authentication follows Kraken's documented API-Key/API-Sign scheme.
See https://docs.kraken.com/rest/
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import httpx

from .config import get_settings


class KrakenAPIError(Exception):
    """Raised when Kraken returns a non-empty error array."""


class KrakenClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        s = get_settings()
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or s.kraken_api_url
        self.timeout = timeout or s.kraken_request_timeout_seconds
        self._client = client or httpx.AsyncClient(timeout=self.timeout)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "KrakenClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ----------------- low-level helpers -----------------

    @staticmethod
    def _nonce() -> str:
        # Kraken requires a strictly increasing nonce; ms epoch is plenty.
        return str(int(time.time() * 1000))

    def _sign(self, path: str, data: dict[str, Any]) -> str:
        if not self.api_secret:
            raise ValueError("api_secret required for private endpoints")
        post_data = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + post_data).encode()
        message = path.encode() + hashlib.sha256(encoded).digest()
        secret = base64.b64decode(self.api_secret)
        signature = hmac.new(secret, message, hashlib.sha512)
        return base64.b64encode(signature.digest()).decode()

    async def _public(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/0/public/{endpoint}"
        resp = await self._client.get(url, params=params or {})
        resp.raise_for_status()
        body = resp.json()
        errors = body.get("error") or []
        if errors:
            raise KrakenAPIError(", ".join(errors))
        return body.get("result", {})

    async def _private(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for private endpoints")
        path = f"/0/private/{endpoint}"
        url = f"{self.base_url}{path}"
        body = dict(data or {})
        body["nonce"] = self._nonce()
        signature = self._sign(path, body)
        headers = {
            "API-Key": self.api_key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = await self._client.post(url, headers=headers, data=body)
        resp.raise_for_status()
        payload = resp.json()
        errors = payload.get("error") or []
        if errors:
            raise KrakenAPIError(", ".join(errors))
        return payload.get("result", {})

    # ----------------- public endpoints -----------------

    async def asset_pairs(self, pair: str | None = None) -> dict[str, Any]:
        params = {"pair": pair} if pair else None
        return await self._public("AssetPairs", params)

    async def ticker(self, pair: str) -> dict[str, Any]:
        return await self._public("Ticker", {"pair": pair})

    # ----------------- private endpoints -----------------

    async def balance(self) -> dict[str, str]:
        return await self._private("Balance")

    async def open_orders(self) -> dict[str, Any]:
        return await self._private("OpenOrders")

    async def closed_orders(self) -> dict[str, Any]:
        return await self._private("ClosedOrders")

    async def add_order(
        self,
        *,
        pair: str,
        side: str,
        ordertype: str,
        volume: float | str,
        price: float | str,
        validate: bool = False,
    ) -> dict[str, Any]:
        if ordertype != "limit":
            raise ValueError("Only limit orders are supported")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        data: dict[str, Any] = {
            "pair": pair,
            "type": side,
            "ordertype": ordertype,
            "volume": str(volume),
            "price": str(price),
        }
        if validate:
            data["validate"] = "true"
        return await self._private("AddOrder", data)

    async def cancel_order(self, txid: str) -> dict[str, Any]:
        return await self._private("CancelOrder", {"txid": txid})


# ---------- helpers used by service / risk layers ----------

# Map common asset symbols to Kraken's pair convention. Kraken returns
# canonical names like "XXBTZUSD", "XETHZUSD", "XRPUSD", "SOLUSD", etc.
# AssetPairs has an "altname" we use ("XBTUSD", "ETHUSD", "XRPUSD", "SOLUSD").
_ASSET_ALIASES = {
    "BTC": "XBT",
    "BITCOIN": "XBT",
    "XBT": "XBT",
    "ETH": "ETH",
    "ETHEREUM": "ETH",
    "XRP": "XRP",
    "RIPPLE": "XRP",
    "SOL": "SOL",
    "SOLANA": "SOL",
    "ADA": "ADA",
    "DOT": "DOT",
    "DOGE": "DOGE",
    "USDT": "USDT",
    "USDC": "USDC",
    "MATIC": "MATIC",
    "LINK": "LINK",
}

_QUOTE_ALIASES = {
    "USD": "USD",
    "USDT": "USDT",
    "USDC": "USDC",
    "EUR": "EUR",
    "GBP": "GBP",
}


def normalize_asset(symbol: str) -> str:
    return _ASSET_ALIASES.get(symbol.strip().upper(), symbol.strip().upper())


def normalize_quote(symbol: str) -> str:
    return _QUOTE_ALIASES.get(symbol.strip().upper(), symbol.strip().upper())


def to_kraken_pair_altname(asset: str, quote: str) -> str:
    """Produce the Kraken pair altname.

    For crypto assets this is ``<ASSET><QUOTE>`` (e.g. ``XBTUSD``, ``XRPUSD``).
    For tokenized-equity (xStocks) tickers Kraken uses ``<TICKER>X<QUOTE>``
    (e.g. ``AAPLXUSD``, ``TSLAXUSD``).
    """
    # Local import to avoid a circular reference at module load time.
    from .equities import is_equity_ticker

    sym = asset.strip().upper()
    q = normalize_quote(quote)
    if is_equity_ticker(sym):
        return f"{sym}X{q}"
    return f"{normalize_asset(asset)}{q}"
