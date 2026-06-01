"""Four-layer profitability analysis for a stock.

Layer 1 — Quality of earnings  (is profit real cash?)
Layer 2 — Moat / sustainability (does it earn high returns consistently?)
Layer 3 — Capital allocation    (is management deploying profit well?)
Layer 4 — Valuation             (is the price fair for the quality?)

…plus a programmatic version of the pre-buy checklist. Every field is best-effort and may
be None; items that genuinely can't be computed (acquisition track record, organic-vs-
inorganic revenue, DCF, true peer P/E) are flagged for human judgment rather than faked.
"""

from __future__ import annotations

import yfinance as yf

from . import screener_metrics, shareholding
from .cache import retry_with_backoff


# --------------------------------------------------------------------------- helpers
def _f(v) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x  # NaN


def _stmt(df, *names):
    """A statement row (oldest→newest) as a list of floats, by the first matching label."""
    if df is None or getattr(df, "empty", True):
        return None
    for name in names:
        if name in df.index:
            cols = sorted(df.columns)  # ascending by date
            return [_f(df.loc[name][c]) for c in cols]
    return None


def _latest(series):
    return series[-1] if series else None


def _growth(series):
    """Latest-vs-previous % growth, ignoring None gaps in the series."""
    vals = [v for v in (series or []) if v is not None]
    if len(vals) < 2 or not vals[-2]:
        return None
    return round((vals[-1] - vals[-2]) / abs(vals[-2]) * 100, 2)


def _cagr(series):
    """CAGR between the oldest and newest non-None points."""
    vals = [v for v in (series or []) if v is not None]
    if len(vals) < 2 or vals[0] <= 0 or vals[-1] <= 0:
        return None
    yrs = len(vals) - 1
    return round(((vals[-1] / vals[0]) ** (1 / yrs) - 1) * 100, 2)


# --------------------------------------------------------------------------- layers
def _earnings_quality(income, cashflow, balance) -> dict:
    revenue = _stmt(income, "Total Revenue", "Operating Revenue")
    gross = _stmt(income, "Gross Profit")
    net_income = _stmt(income, "Net Income", "Net Income Common Stockholders")
    ocf = _stmt(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
    receivables = _stmt(balance, "Accounts Receivable", "Net Receivables", "Receivables")

    ni, oc = _latest(net_income), _latest(ocf)
    cash_conversion = round(oc / ni, 2) if (oc is not None and ni and ni > 0) else None

    margin_trend = None
    if revenue and gross and len(revenue) == len(gross):
        margin_trend = [
            {"year_index": i, "margin": round(g / r * 100, 1)}
            for i, (g, r) in enumerate(zip(gross, revenue))
            if r
        ]
    direction = None
    if margin_trend and len(margin_trend) >= 2:
        delta = margin_trend[-1]["margin"] - margin_trend[0]["margin"]
        direction = "expanding" if delta > 2 else "shrinking" if delta < -2 else "stable"

    rev_g = _growth(revenue)
    recv_g = _growth(receivables)
    # Receivables outpacing revenue can mean sales booked but not collected.
    recv_flag = recv_g is not None and rev_g is not None and recv_g > rev_g + 5

    return {
        "net_income": ni,
        "operating_cash_flow": oc,
        "cash_conversion": cash_conversion,
        "gross_margin_trend": margin_trend,
        "gross_margin_direction": direction,
        "revenue_growth_yoy": rev_g,
        "receivables_growth_yoy": recv_g,
        "receivables_outpacing_revenue": recv_flag,
        "revenue_cagr": _cagr(revenue),
    }


def _moat(ticker: str) -> dict:
    roce = screener_metrics.get_roce_history(ticker)
    vals = [v for v in roce.get("roce", []) if v is not None] if roce.get("available") else []
    last5 = vals[-5:]
    return {
        "roce_available": bool(vals),
        "roce_history": roce.get("roce", []),
        "roce_years": roce.get("years", []),
        "roce_latest": vals[-1] if vals else None,
        "roce_avg_5y": round(sum(last5) / len(last5), 1) if last5 else None,
        "roce_consistent_15": bool(last5) and all(v >= 15 for v in last5),
        "years_above_15": sum(1 for v in vals if v >= 15),
        "years_total": len(vals),
        "source": roce.get("source"),
    }


def _capital_allocation(ticker: str, info: dict) -> dict:
    raw_de = _f(info.get("debtToEquity"))           # yfinance reports this as a percentage
    de_x = round(raw_de / 100, 2) if raw_de is not None else None
    payout = _f(info.get("payoutRatio"))
    div_yield = _f(info.get("dividendYield"))

    promoter_latest = promoter_trend = None
    sh = shareholding.get_shareholding(ticker)
    if sh.get("available"):
        for cat in sh.get("categories", []):
            if cat["label"].lower().startswith("promoter"):
                vals = [v for v in cat["values"] if v is not None]
                if vals:
                    promoter_latest = vals[-1]
                    if len(vals) >= 2:
                        delta = vals[-1] - vals[0]
                        promoter_trend = "rising" if delta > 0.5 else "falling" if delta < -0.5 else "stable"
                break

    return {
        "debt_equity_x": de_x,
        "payout_ratio": round(payout * 100, 1) if payout is not None else None,
        "reinvestment_rate": round((1 - payout) * 100, 1) if payout is not None and payout <= 1 else None,
        "dividend_yield": round(div_yield, 2) if div_yield is not None else None,
        "promoter_holding": promoter_latest,
        "promoter_trend": promoter_trend,
    }


def _valuation(info: dict, cashflow) -> dict:
    pe = _f(info.get("trailingPE"))
    peg = _f(info.get("trailingPegRatio")) or _f(info.get("pegRatio"))
    if peg is None:
        eg = _f(info.get("earningsGrowth"))
        if pe and eg and eg > 0:
            peg = round(pe / (eg * 100), 2)
    ev_ebitda = _f(info.get("enterpriseToEbitda"))

    fcf_series = _stmt(cashflow, "Free Cash Flow")
    fcf = _latest(fcf_series)
    if fcf is None:
        ocf = _latest(_stmt(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities"))
        capex = _latest(_stmt(cashflow, "Capital Expenditure", "Capital Expenditures"))
        if ocf is not None and capex is not None:
            fcf = ocf - abs(capex)
    mcap = _f(info.get("marketCap"))
    p_fcf = round(mcap / fcf, 1) if (mcap and fcf and fcf > 0) else None

    return {
        "pe_ratio": round(pe, 2) if pe else None,
        "peg_ratio": round(peg, 2) if peg else None,
        "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
        "price_to_fcf": p_fcf,
        "free_cash_flow": fcf,
    }


# --------------------------------------------------------------------------- checklist
def _check(label, status, detail):
    return {"label": label, "status": status, "detail": detail}


def _build_checklist(eq, moat, cap, val, peers) -> list[dict]:
    items = []

    cagr = eq["revenue_cagr"]
    items.append(_check(
        "Revenue growing consistently",
        "pass" if (cagr or 0) > 5 else "warn" if (cagr or -1) >= 0 else "fail" if cagr is not None else "info",
        f"{cagr}% revenue CAGR over available years" if cagr is not None else "Not enough data",
    ))

    cc = eq["cash_conversion"]
    items.append(_check(
        "Operating cash flow ≥ net income",
        "pass" if cc is not None and cc >= 1 else "warn" if cc is not None and cc >= 0.8 else "fail" if cc is not None else "info",
        f"OCF/Net income = {cc}×" if cc is not None else "Cash flow vs income unavailable",
    ))

    d = eq["gross_margin_direction"]
    items.append(_check(
        "Gross margins stable or expanding",
        "pass" if d in ("expanding", "stable") else "warn" if d == "shrinking" else "info",
        f"Gross margin {d}" if d else "Gross-margin history unavailable",
    ))

    if moat["roce_available"]:
        consistent = moat["roce_consistent_15"]
        avg = moat["roce_avg_5y"]
        items.append(_check(
            "ROCE > 15% consistently (moat test)",
            "pass" if consistent else "warn" if (avg or 0) >= 15 else "fail",
            f"{moat['years_above_15']}/{moat['years_total']} yrs ≥15%; 5y avg {avg}%",
        ))
    else:
        items.append(_check("ROCE > 15% consistently (moat test)", "info", "ROCE history unavailable"))

    de = cap["debt_equity_x"]
    items.append(_check(
        "Debt/Equity < 1",
        "pass" if de is not None and de < 1 else "warn" if de is not None and de < 2 else "fail" if de is not None else "info",
        f"D/E = {de}×" if de is not None else "Debt/Equity unavailable",
    ))

    pt = cap["promoter_trend"]
    items.append(_check(
        "Promoter holding stable/increasing",
        "pass" if pt in ("rising", "stable") else "warn" if pt == "falling" else "info",
        f"Promoters {cap['promoter_holding']}% ({pt})" if pt else "Promoter trend unavailable",
    ))

    pe = val["pe_ratio"]
    med_pe = peers.get("median_pe") if peers.get("available") else None
    if pe and med_pe:
        disc = round((pe / med_pe - 1) * 100)
        if pe <= med_pe:
            status, word = "pass", f"{abs(disc)}% below"
        elif pe <= med_pe * 1.5:
            status, word = "warn", f"{disc}% above"
        else:
            status, word = "warn", f"{disc}% above"
        items.append(_check(
            "P/E reasonable vs peers",
            status,
            f"P/E {pe} is {word} the peer median ({med_pe})",
        ))
    else:
        items.append(_check(
            "P/E reasonable (vs history & peers)",
            "info",
            f"P/E {pe} — compare to the stock's own history and sector peers" if pe else "P/E unavailable; judge vs peers",
        ))

    items.append(_check(
        "Can you explain the moat?",
        "pass" if moat["roce_consistent_15"] else "info",
        "High, durable ROCE suggests a moat — but name it (brand, cost, switching, network)."
        if moat["roce_consistent_15"] else "Articulate why competitors can't erode returns.",
    ))

    items.append(_check(
        "Do you understand what could go wrong?",
        "info",
        "Your judgment: list the 2–3 risks that would break the thesis.",
    ))

    return items


def get_quality_analysis(ticker: str) -> dict:
    """Assemble the four-layer profitability analysis + checklist for a ticker."""
    tk = yf.Ticker(ticker)

    def _safe(getter):
        try:
            return retry_with_backoff(getter)
        except Exception:  # noqa: BLE001
            return None

    info = _safe(lambda: tk.info) or {}
    income = _safe(lambda: tk.income_stmt)
    cashflow = _safe(lambda: tk.cashflow)
    balance = _safe(lambda: tk.balance_sheet)

    eq = _earnings_quality(income, cashflow, balance)
    moat = _moat(ticker)
    cap = _capital_allocation(ticker, info)
    val = _valuation(info, cashflow)
    peers = screener_metrics.get_peers(ticker)
    checklist = _build_checklist(eq, moat, cap, val, peers)
    score = sum(1 for c in checklist if c["status"] == "pass")

    return {
        "ticker": ticker,
        "earnings_quality": eq,
        "moat": moat,
        "capital_allocation": cap,
        "valuation": val,
        "peers": peers,
        "checklist": checklist,
        "checklist_score": score,
        "checklist_total": len([c for c in checklist if c["status"] != "info"]),
    }
