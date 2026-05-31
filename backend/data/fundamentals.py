"""Richer fundamentals from yfinance — quarterly results trend + key ratios.

These are the heavier yfinance calls (full financial statements), so they live behind a
separate endpoint the StockPage fetches lazily, keeping the main /stock call fast.
"""

from __future__ import annotations

import yfinance as yf

from .cache import retry_with_backoff


def _f(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check


def _row(df, *names):
    """Return a statement row by the first matching label, or None."""
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def get_quarterly_results(ticker: str) -> dict:
    """Up to ~5 recent quarters: revenue, operating profit, OPM%, net profit, EPS."""
    try:
        stmt = retry_with_backoff(lambda: yf.Ticker(ticker).quarterly_income_stmt)
    except Exception:  # noqa: BLE001
        return {"available": False, "quarters": [], "rows": {}}

    if stmt is None or stmt.empty:
        return {"available": False, "quarters": [], "rows": {}}

    # Columns are quarter-end timestamps but not guaranteed sorted — sort oldest→newest.
    cols = sorted(stmt.columns)
    quarters = [c.strftime("%b %Y") for c in cols]

    revenue = _row(stmt, "Total Revenue", "Operating Revenue")
    op_income = _row(stmt, "Operating Income", "EBIT")
    net_income = _row(stmt, "Net Income", "Net Income Common Stockholders")
    eps = _row(stmt, "Diluted EPS", "Basic EPS")

    def series(row):
        return [_f(row[c]) if row is not None else None for c in cols]

    rev = series(revenue)
    opi = series(op_income)
    opm = [
        round(o / r * 100, 2) if (o is not None and r) else None
        for o, r in zip(opi, rev)
    ]

    return {
        "available": True,
        "quarters": quarters,
        "rows": {
            "revenue": rev,
            "operating_profit": opi,
            "opm_pct": opm,
            "net_profit": series(net_income),
            "eps": series(eps),
        },
    }


def get_key_ratios(ticker: str) -> dict:
    """Headline ratios from .info, plus a best-effort ROCE and revenue CAGR."""
    tk = yf.Ticker(ticker)
    try:
        info = retry_with_backoff(lambda: tk.info)
    except Exception:  # noqa: BLE001
        info = {}

    roe = _f(info.get("returnOnEquity"))
    div_yield = _f(info.get("dividendYield"))

    return {
        "roe": round(roe * 100, 2) if roe is not None else None,
        "roce": _compute_roce(tk),
        "book_value": _f(info.get("bookValue")),
        "price_to_book": _f(info.get("priceToBook")),
        "dividend_yield": round(div_yield, 2) if div_yield is not None else None,
        "pe_ratio": _f(info.get("trailingPE")),
        "revenue_growth_yoy": _pct(info.get("revenueGrowth")),
        "earnings_growth_yoy": _pct(info.get("earningsGrowth")),
        "revenue_cagr_3y": _revenue_cagr(tk),
    }


def _pct(value) -> float | None:
    f = _f(value)
    return round(f * 100, 2) if f is not None else None


def _compute_roce(tk: yf.Ticker) -> float | None:
    """ROCE ≈ EBIT / (Total Assets − Current Liabilities). Best-effort; None if unavailable."""
    try:
        inc = retry_with_backoff(lambda: tk.income_stmt)
        bs = retry_with_backoff(lambda: tk.balance_sheet)
        ebit_row = _row(inc, "EBIT", "Operating Income")
        assets_row = _row(bs, "Total Assets")
        curr_liab_row = _row(bs, "Current Liabilities", "Total Current Liabilities")
        if ebit_row is None or assets_row is None or curr_liab_row is None:
            return None
        ebit = _f(ebit_row.iloc[0])
        capital_employed = _f(assets_row.iloc[0]) - _f(curr_liab_row.iloc[0])
        if not ebit or not capital_employed:
            return None
        return round(ebit / capital_employed * 100, 2)
    except Exception:  # noqa: BLE001
        return None


def _revenue_cagr(tk: yf.Ticker) -> float | None:
    """Revenue CAGR across the ~4 annual periods yfinance provides. None if too few."""
    try:
        inc = retry_with_backoff(lambda: tk.income_stmt)
        rev = _row(inc, "Total Revenue", "Operating Revenue")
        if rev is None or len(rev) < 2:
            return None
        newest = _f(rev.iloc[0])
        oldest = _f(rev.iloc[-1])
        years = len(rev) - 1
        if not newest or not oldest or oldest <= 0:
            return None
        return round(((newest / oldest) ** (1 / years) - 1) * 100, 2)
    except Exception:  # noqa: BLE001
        return None
