"""Tokenized-equity (xStocks) support for Kraken.

Kraken lists tokenized equities — "xStocks" — as regular trading pairs on its
REST exchange. The symbol convention is `<TICKER>x` for the token (e.g.
`AAPLx`) and `<TICKER>XUSD` for the spot pair (e.g. `AAPLXUSD`).

Important caveats users should be aware of:
- xStocks are tokenized representations of equities issued by Backed Finance
  on Solana, not direct ownership of NYSE/Nasdaq shares.
- They typically do not carry voting rights; dividends are handled by the
  token issuer.
- Availability varies by jurisdiction (notably restricted for US persons).
- Pairs trade 24/7 like crypto but reference an underlying that does not.

The lists below are conservative and easy to extend. We deliberately do NOT
hard-code every xStock — we keep the parser-side allowlist tight and let
unknown tickers fail at the Kraken AddOrder call with a precise error.
"""
from __future__ import annotations

# Canonical equity tickers supported by the parser. Add to this set as Kraken
# expands its xStocks listings.
SUPPORTED_EQUITY_TICKERS: set[str] = {
    # Mega-caps
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    # Other common single-names
    "COIN", "MSTR", "PLTR", "AMD", "INTC", "NFLX", "DIS", "BA",
    "JPM", "V", "MA", "BAC", "WMT", "XOM", "CVX",
    # ETFs
    "SPY", "QQQ", "IWM", "DIA", "VTI", "GLD", "SLV", "TLT",
}

# Aliases users might type for popular names. Map to canonical ticker.
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


def is_equity_ticker(symbol: str) -> bool:
    """Returns True if `symbol` is a recognised xStocks ticker (case-insensitive)."""
    if not symbol:
        return False
    return symbol.strip().upper() in SUPPORTED_EQUITY_TICKERS


def normalize_equity_ticker(symbol: str) -> str | None:
    """Normalise an alias or ticker to its canonical xStocks ticker, or None."""
    if not symbol:
        return None
    s = symbol.strip().lower()
    if s in EQUITY_ALIASES:
        return EQUITY_ALIASES[s]
    upper = s.upper()
    if upper in SUPPORTED_EQUITY_TICKERS:
        return upper
    return None


def kraken_xstocks_pair(ticker: str, quote: str = "USD") -> str:
    """Build the Kraken xStocks pair altname (e.g. AAPLXUSD)."""
    return f"{ticker.upper()}X{quote.upper()}"


# Disclosure shown in the preview/confirmation flow whenever an equity order is built.
EQUITY_DISCLOSURE = (
    "xStocks are tokenized equities issued on Solana by Backed Finance. "
    "They do not represent direct share ownership and may not be available "
    "in all jurisdictions (notably restricted for US persons)."
)
