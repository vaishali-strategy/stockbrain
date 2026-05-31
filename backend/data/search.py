"""Ticker search — Indian (NSE/BSE) first.

The PRIMARY path is an offline fuzzy match against the bundled ``nifty500_tickers.json``
(``yfinance.search()`` is unreliable for Indian names). If the query already looks like a
symbol we probe ``.NS`` then ``.BO`` directly, and only fall back to ``yfinance.search()``
as a last resort. The raw ``.NS``/``.BO`` suffix is never shown to the user — we surface a
clean "NSE"/"BSE" exchange badge instead.
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import yfinance as yf

from .cache import retry_with_backoff

_TICKERS_PATH = Path(__file__).resolve().parent / "nifty500_tickers.json"
_MAX_RESULTS = 10


@lru_cache(maxsize=1)
def _load_universe() -> list[dict]:
    """Load and cache the bundled Nifty 500 list. Empty list if the file is missing."""
    if not _TICKERS_PATH.exists():
        return []
    try:
        return json.loads(_TICKERS_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []


def _exchange_for(ticker: str) -> str:
    if ticker.endswith(".NS"):
        return "NSE"
    if ticker.endswith(".BO"):
        return "BSE"
    return ""


def _market_cap_category(_ticker: str) -> str:
    # Placeholder bucket — refined later when we wire live market-cap into search.
    return "unknown"


def _to_result(row: dict) -> dict:
    return {
        "ticker": row["ticker"],
        "name": row.get("name", row["ticker"]),
        "exchange": _exchange_for(row["ticker"]),
        "sector": row.get("sector", ""),
        "market_cap_category": _market_cap_category(row["ticker"]),
    }


def _score(query: str, name: str, symbol: str) -> float:
    """Relevance score in [0, 1+]. Substring/prefix hits beat fuzzy similarity."""
    q = query.lower().strip()
    name_l = name.lower()
    sym_l = symbol.lower()
    if q == sym_l or q == name_l:
        return 1.5
    if sym_l.startswith(q) or name_l.startswith(q):
        return 1.2
    if q in name_l or q in sym_l:
        return 1.0
    return SequenceMatcher(None, q, name_l).ratio()


def _looks_like_ticker(query: str) -> bool:
    """A short alphanumeric token with no spaces is probably a raw symbol."""
    q = query.strip()
    return bool(q) and " " not in q and len(q) <= 12 and q.replace("&", "").replace("-", "").isalnum()


def _probe_direct(symbol: str) -> dict | None:
    """Try ``{symbol}.NS`` then ``{symbol}.BO`` directly via yfinance fast_info."""
    for suffix, exch in ((".NS", "NSE"), (".BO", "BSE")):
        candidate = f"{symbol.upper()}{suffix}"
        try:
            fast = retry_with_backoff(lambda: yf.Ticker(candidate).fast_info)
            if getattr(fast, "last_price", None):
                return {
                    "ticker": candidate,
                    "name": symbol.upper(),
                    "exchange": exch,
                    "sector": "",
                    "market_cap_category": "unknown",
                }
        except Exception:  # noqa: BLE001 — probe failure just means try the next suffix.
            continue
    return None


def search_ticker(query: str) -> list[dict]:
    """Return up to 10 matching tickers, NSE/BSE prioritized."""
    query = (query or "").strip()
    if not query:
        return []

    universe = _load_universe()

    # 1) PRIMARY: fuzzy-match the bundled list.
    scored = [
        (_score(query, row.get("name", ""), row["ticker"].split(".")[0]), row)
        for row in universe
    ]
    matches = [row for (s, row) in sorted(scored, key=lambda x: x[0], reverse=True) if s >= 0.5]
    results = [_to_result(row) for row in matches[:_MAX_RESULTS]]
    if results:
        return results

    # 2) The query looks like a symbol — probe NSE then BSE directly.
    if _looks_like_ticker(query):
        direct = _probe_direct(query)
        if direct:
            return [direct]

    # 3) LAST RESORT: yfinance.search(), filtered to .NS/.BO only.
    try:
        raw = retry_with_backoff(lambda: yf.Search(query).quotes) or []
        out = []
        for q in raw:
            sym = q.get("symbol", "")
            if sym.endswith((".NS", ".BO")):
                out.append({
                    "ticker": sym,
                    "name": q.get("longname") or q.get("shortname") or sym,
                    "exchange": _exchange_for(sym),
                    "sector": q.get("sector", ""),
                    "market_cap_category": "unknown",
                })
            if len(out) >= _MAX_RESULTS:
                break
        return out
    except Exception:  # noqa: BLE001 — search is best-effort; empty result is acceptable.
        return []
