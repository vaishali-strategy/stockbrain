"""Turn a screened candidate into a structured SignalScore.

Adds fundamentals (P/E, margins, growth) from yfinance, then classifies the stock as
BUY / SELL / WATCH with a HIGH / MEDIUM / LOW confidence based on how many indicators agree.
The classification logic is pure and side-effect-free so it can be unit-tested directly.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import yfinance as yf

from ..data.cache import retry_with_backoff

# Signal-type thresholds (from the build brief).
_BUY_RSI = 38
_BUY_VS50_FLOOR = -8
_BUY_PE_CEILING = 40
_SELL_RSI = 65
_SELL_VS50_FLOOR = 5
_SELL_FROM_HIGH_FLOOR = -5

_VOLUME_SPIKE = 2.0
_IST = timezone(timedelta(hours=5, minutes=30))


def classify_signal(rsi, vs_50dma, pe_ratio, pct_from_52w_high) -> str:
    """BUY / SELL / WATCH from the core indicators. Pure function (unit-tested)."""
    vs50 = vs_50dma if vs_50dma is not None else 0.0
    from_high = pct_from_52w_high if pct_from_52w_high is not None else -100.0
    pe_ok_for_buy = pe_ratio is None or pe_ratio < _BUY_PE_CEILING

    if rsi is not None and rsi < _BUY_RSI and vs50 > _BUY_VS50_FLOOR and pe_ok_for_buy:
        return "BUY"
    if (
        rsi is not None
        and rsi > _SELL_RSI
        and vs50 > _SELL_VS50_FLOOR
        and from_high > _SELL_FROM_HIGH_FLOOR
    ):
        return "SELL"
    return "WATCH"


def classify_confidence(cand: dict) -> str:
    """HIGH/MEDIUM/LOW from how many indicators agree. Pure function (unit-tested)."""
    signals = 0
    rsi = cand.get("rsi")
    if rsi is not None and (rsi < 35 or rsi > 68):
        signals += 1
    vr = cand.get("volume_ratio")
    if vr is not None and vr >= _VOLUME_SPIKE:
        signals += 1
    if cand.get("ma_cross_up"):
        signals += 1
    price = cand.get("current_price")
    low = cand.get("week52_low")
    high = cand.get("week52_high")
    if price and low and price <= low * 1.05:
        signals += 1
    if price and high and price >= high * 0.97:
        signals += 1

    if signals >= 3:
        return "HIGH"
    if signals == 2:
        return "MEDIUM"
    return "LOW"


def _fundamentals(ticker: str) -> dict:
    """P/E, net margin, revenue growth from yfinance .info (any may be None)."""
    try:
        info = retry_with_backoff(lambda: yf.Ticker(ticker).info)
    except Exception:  # noqa: BLE001
        return {"pe_ratio": None, "net_margin": None, "revenue_growth_yoy": None}
    net = info.get("profitMargins")
    rev = info.get("revenueGrowth")
    return {
        "pe_ratio": _round(info.get("trailingPE")),
        "net_margin": _round(net * 100) if isinstance(net, (int, float)) else None,
        "revenue_growth_yoy": _round(rev * 100) if isinstance(rev, (int, float)) else None,
    }


def _technicals_summary(cand: dict) -> str:
    bits = []
    rsi = cand.get("rsi")
    if rsi is not None:
        if rsi < 35:
            bits.append("oversold on RSI")
        elif rsi > 68:
            bits.append("overbought on RSI")
    if cand.get("volume_ratio") and cand["volume_ratio"] >= _VOLUME_SPIKE:
        bits.append("volume surge")
    if cand.get("ma_cross_up"):
        bits.append("crossed above 50-DMA")
    price, low, high = cand.get("current_price"), cand.get("week52_low"), cand.get("week52_high")
    if price and low and price <= low * 1.05:
        bits.append("near 52-week support")
    if price and high and price >= high * 0.97:
        bits.append("near 52-week high")
    return _sentence_case(", ".join(bits)) if bits else "Mixed technical picture"


def _fundamentals_summary(f: dict) -> str:
    margin, growth = f.get("net_margin"), f.get("revenue_growth_yoy")
    if margin is None and growth is None:
        return "Limited fundamental data"
    parts = []
    if margin is not None:
        parts.append(("healthy" if margin >= 10 else "thin") + f" net margin {margin}%")
    if growth is not None:
        parts.append(("strong" if growth >= 10 else "modest") + f" revenue growth {growth}%")
    return _sentence_case(", ".join(parts))


def _sentence_case(text: str) -> str:
    """Upper-case only the first character (unlike str.capitalize, which lowercases the rest)."""
    return text[:1].upper() + text[1:] if text else text


def score_candidate(cand: dict, vault_has_notes: bool = False) -> dict:
    """Build the full SignalScore for one screened candidate."""
    f = _fundamentals(cand["ticker"])
    signal_type = classify_signal(
        cand.get("rsi"), cand.get("vs_50dma"), f["pe_ratio"], cand.get("pct_from_52w_high")
    )
    confidence = classify_confidence(cand)
    return {
        "ticker": cand["ticker"],
        "display_name": cand["display_name"],
        "sector": cand.get("sector", ""),
        "signal_type": signal_type,
        "confidence": confidence,
        "current_price": cand.get("current_price"),
        "change_pct_today": cand.get("change_pct_today"),
        "rsi": cand.get("rsi"),
        "vs_50dma": cand.get("vs_50dma"),
        "vs_200dma": cand.get("vs_200dma"),
        "volume_ratio": cand.get("volume_ratio"),
        "pe_ratio": f["pe_ratio"],
        "week52_high": cand.get("week52_high"),
        "week52_low": cand.get("week52_low"),
        "pct_from_52w_high": cand.get("pct_from_52w_high"),
        "revenue_growth_yoy": f["revenue_growth_yoy"],
        "net_margin": f["net_margin"],
        "technicals_summary": _technicals_summary(cand),
        "fundamentals_summary": _fundamentals_summary(f),
        "vault_has_notes": vault_has_notes,
        "scored_at": datetime.now(_IST).isoformat(),
    }


def _round(v, n: int = 2):
    if not isinstance(v, (int, float)):
        return None
    f = float(v)
    return None if f != f else round(f, n)
