"""Tokenized-equity (xStocks) support for Kraken.

Kraken lists tokenized equities — "xStocks" — as regular trading pairs on its
REST exchange. The symbol convention is ``<TICKER>x`` for the token (e.g.
``AAPLx``) and ``<TICKER>XUSD`` for the spot pair (e.g. ``AAPLXUSD``).

Important caveats users should be aware of:
- xStocks are tokenized representations of equities issued by Backed Finance
  on Solana, not direct ownership of NYSE/Nasdaq shares.
- They typically do not carry voting rights; dividends are handled by the
  token issuer.
- Availability varies by jurisdiction (notably restricted for US persons).
- Pairs trade 24/7 like crypto but reference an underlying that does not.

The supported-ticker list is **discovered at runtime** from Kraken's public
``/0/public/AssetPairs`` endpoint. The static ``FALLBACK_EQUITY_TICKERS`` set
below is used only when discovery has not yet succeeded (e.g. on first boot
before the background refresh runs, or if Kraken is unreachable).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .kraken_client import KrakenClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static fallback list — used only if discovery has not yet populated the
# registry. Kept conservative: when in doubt, the parser will reject and the
# user can refresh.
# ---------------------------------------------------------------------------

FALLBACK_EQUITY_TICKERS: set[str] = {
    # Mega-caps
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    # Other common single-names
    "COIN", "MSTR", "PLTR", "AMD", "INTC", "NFLX", "DIS", "BA",
    "JPM", "V", "MA", "BAC", "WMT", "XOM", "CVX",
    # ETFs
    "SPY", "QQQ", "IWM", "DIA", "VTI", "GLD", "SLV", "TLT",
}

# Aliases users might type for popular names. Map to canonical ticker.
# These cover common natural-language names; the registry handles the rest.
EQUITY_ALIASES: dict[str, str] = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META", "facebook": "META",
    "tesla": "TSLA",
    "coinbase": "COIN",
    "microstrategy": "MSTR", "strategy": "MSTR",
    "palantir": "PLTR",
    "netflix": "NFLX",
    "disney": "DIS",
    "boeing": "BA",
    "walmart": "WMT",
    "exxon": "XOM",
}

# Disclosure shown in the preview/confirmation flow whenever an equity order is
# built. Surfaces in ParsedCommand.warnings.
EQUITY_DISCLOSURE = (
    "xStocks are tokenized equities issued on Solana by Backed Finance. "
    "They do not represent direct share ownership and may not be available "
    "in all jurisdictions (notably restricted for US persons)."
)

# Quote currencies we accept for an xStocks pair. These are the suffixes
# Kraken returns in the asset_pairs() ``quote`` field.
_EQUITY_QUOTE_FIELDS = {"ZUSD", "USD", "USDT", "USDC", "ZEUR", "EUR"}

# Bases we *never* treat as equities even if they end in 'X'. Built from the
# crypto symbols already handled elsewhere; keeps the discovery filter from
# accidentally classifying a coincidental crypto pair as an xStock.
_CRYPTO_BASES_TO_EXCLUDE = {
    "XBT", "XXBT",  # Bitcoin
    "XETH", "XXRP", "XLTC", "XXLM", "XZEC",  # legacy X-prefixed cryptos
}


# ---------------------------------------------------------------------------
# Discovery filter
# ---------------------------------------------------------------------------

def _filter_xstocks_from_asset_pairs(asset_pairs: dict[str, Any]) -> set[str]:
    """Extract the set of xStocks ticker symbols from an /AssetPairs response.

    A pair is treated as an xStock when:
    - the ``base`` field ends in literal ``"X"`` (e.g. ``"AAPLX"``)
    - the ``quote`` field is one of the recognised fiat/stable quotes
    - the base does not start with Kraken's legacy ``X``/``Z`` prefix
      (those are reserved for crypto/fiat)
    - the base is at least 3 characters (so ``"X"`` alone doesn't slip in)
    - the base is not an explicitly excluded crypto symbol

    The returned tickers have the trailing ``X`` stripped (so ``AAPLX`` → ``AAPL``).
    """
    tickers: set[str] = set()
    for pair_name, info in asset_pairs.items():
        base = (info.get("base") or "").upper()
        quote = (info.get("quote") or "").upper()
        if not base or not quote:
            continue
        if quote not in _EQUITY_QUOTE_FIELDS:
            continue
        if not base.endswith("X"):
            continue
        # Drop Kraken legacy-prefixed bases (XXBT, XETH, XXRP, XLTC, XZEC, XDG, XMR…)
        if base.startswith(("X", "Z")) and len(base) <= 5:
            continue
        if base in _CRYPTO_BASES_TO_EXCLUDE:
            continue
        if len(base) < 3:
            continue
        ticker = base[:-1]  # strip trailing 'X'
        # Guard against pathological cases like base == "X"
        if not ticker:
            continue
        tickers.add(ticker)
    return tickers


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class EquityRegistryStatus:
    """Snapshot of the registry's current state. Safe to JSON-serialise."""

    fetched_at: datetime | None
    last_error: str | None
    ticker_count: int
    using_fallback: bool


@dataclass
class EquityRegistry:
    """Process-wide cache of xStocks tickers discovered from Kraken.

    Read paths (``tickers()``, ``is_supported()``) are non-blocking and never
    fail: if a refresh has not yet succeeded, they fall back to the static
    list. The write path (``refresh()``) is guarded by an asyncio lock so a
    concurrent boot + manual refresh don't race.
    """

    _tickers: set[str] = field(default_factory=set)
    _fetched_at: datetime | None = None
    _last_error: str | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # Pluggable so tests can inject a fake clock.
    _now_fn: Any = datetime.utcnow

    def tickers(self) -> set[str]:
        """Return discovered tickers UNION the curated fallback.

        Both serve. This means:
        - If discovery has not yet run, the fallback list works.
        - If discovery succeeds, we accept *more* tickers (Kraken might list
          xStocks our fallback hasn't been updated for yet).
        - If Kraken later delists something, the fallback still keeps it
          working until the next code update — the AddOrder call will then
          surface the precise "Unknown asset pair" error from Kraken.
        """
        return self._tickers | FALLBACK_EQUITY_TICKERS

    def discovered_tickers(self) -> set[str]:
        """Tickers discovered from Kraken on the latest successful refresh.
        Empty if discovery has never succeeded."""
        return set(self._tickers)

    def is_supported(self, symbol: str) -> bool:
        if not symbol:
            return False
        return symbol.strip().upper() in self.tickers()

    def status(self) -> EquityRegistryStatus:
        return EquityRegistryStatus(
            fetched_at=self._fetched_at,
            last_error=self._last_error,
            ticker_count=len(self.tickers()),
            using_fallback=not self._tickers,
        )

    async def refresh(self, client: "KrakenClient") -> EquityRegistryStatus:
        """Re-fetch /AssetPairs and replace the cache. Never raises."""
        async with self._lock:
            try:
                data = await client.asset_pairs()
                discovered = _filter_xstocks_from_asset_pairs(data)
                if not discovered:
                    raise ValueError("No xStocks pairs found in AssetPairs response")
                self._tickers = discovered
                self._fetched_at = self._now_fn()
                self._last_error = None
                logger.info("EquityRegistry refreshed: %d tickers", len(discovered))
            except Exception as exc:  # network, parse, or empty result
                self._last_error = str(exc)
                logger.warning("EquityRegistry refresh failed: %s", exc)
            return self.status()

    def is_stale(self, ttl: timedelta) -> bool:
        if self._fetched_at is None:
            return True
        return (self._now_fn() - self._fetched_at) > ttl


# A single process-wide instance.
_REGISTRY = EquityRegistry()


def get_registry() -> EquityRegistry:
    return _REGISTRY


# ---------------------------------------------------------------------------
# Public helpers used by parser / kraken_client
# ---------------------------------------------------------------------------

def is_equity_ticker(symbol: str) -> bool:
    """Returns True if ``symbol`` is a recognised xStocks ticker (case-insensitive)."""
    return _REGISTRY.is_supported(symbol)


def normalize_equity_ticker(symbol: str) -> str | None:
    """Normalise an alias or ticker to its canonical xStocks ticker, or None."""
    if not symbol:
        return None
    s = symbol.strip().lower()
    if s in EQUITY_ALIASES:
        candidate = EQUITY_ALIASES[s]
        return candidate if _REGISTRY.is_supported(candidate) else None
    upper = s.upper()
    if _REGISTRY.is_supported(upper):
        return upper
    return None


def kraken_xstocks_pair(ticker: str, quote: str = "USD") -> str:
    """Build the Kraken xStocks pair altname (e.g. ``AAPLXUSD``)."""
    return f"{ticker.upper()}X{quote.upper()}"
