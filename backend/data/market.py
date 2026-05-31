"""Live market data via yfinance — quotes, history, and financials.

All history reads delegate to ``cache.py`` (SQLite-backed, rate-limit friendly). Quote
and financials use yfinance's ``fast_info``/``info`` wrapped in ``retry_with_backoff``.
Every function returns plain JSON-able dicts and degrades to an ``{"error": ...}`` shape
rather than raising, so the API layer never has to handle yfinance exceptions.
"""

from __future__ import annotations

import yfinance as yf

from .cache import get_history as _cached_history
from .cache import retry_with_backoff


def _err(ticker: str) -> dict:
    return {"error": f"Could not fetch data for {ticker}"}


def get_quote(ticker: str) -> dict:
    """Current price, % change, volume, market cap, P/E, 52-week range.

    Prices for ``.NS``/``.BO`` tickers are already in INR — returned as-is.
    """
    try:
        tk = yf.Ticker(ticker)
        fast = retry_with_backoff(lambda: tk.fast_info)
        price = _f(getattr(fast, "last_price", None))
        prev_close = _f(getattr(fast, "previous_close", None))
        if price is None:
            return _err(ticker)

        change_pct = (
            round((price - prev_close) / prev_close * 100, 2)
            if prev_close not in (None, 0)
            else None
        )

        # P/E isn't in fast_info; pull from .info but tolerate it being unavailable.
        pe_ratio = None
        try:
            info = retry_with_backoff(lambda: tk.info)
            pe_ratio = _f(info.get("trailingPE"))
        except Exception:  # noqa: BLE001 — .info is flaky; quote still useful without P/E.
            info = {}

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "previous_close": round(prev_close, 2) if prev_close is not None else None,
            "change_pct": change_pct,
            "volume": _i(getattr(fast, "last_volume", None)),
            "market_cap": _i(getattr(fast, "market_cap", None)),
            "pe_ratio": round(pe_ratio, 2) if pe_ratio is not None else None,
            "week52_high": _f(getattr(fast, "year_high", None)),
            "week52_low": _f(getattr(fast, "year_low", None)),
            "currency": getattr(fast, "currency", None) or "INR",
        }
    except Exception:  # noqa: BLE001
        return _err(ticker)


def get_history(ticker: str, period: str = "3mo") -> list[dict]:
    """Daily OHLCV over ``period``, served through the on-disk cache."""
    return _cached_history(ticker, period)


def get_financials(ticker: str) -> dict:
    """Revenue (TTM), gross/net margin, EPS (TTM), debt/equity — any may be None."""
    try:
        info = retry_with_backoff(lambda: yf.Ticker(ticker).info)
    except Exception:  # noqa: BLE001
        return {
            "revenue_ttm": None, "gross_margin": None, "net_margin": None,
            "eps_ttm": None, "debt_equity": None,
        }

    gross = _f(info.get("grossMargins"))
    net = _f(info.get("profitMargins"))
    return {
        "revenue_ttm": _i(info.get("totalRevenue")),
        "gross_margin": round(gross * 100, 2) if gross is not None else None,
        "net_margin": round(net * 100, 2) if net is not None else None,
        "eps_ttm": _f(info.get("trailingEps")),
        "debt_equity": _f(info.get("debtToEquity")),
    }


def _f(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check


def _i(value) -> int | None:
    f = _f(value)
    return int(f) if f is not None else None
