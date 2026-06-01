"""Screen the Nifty 500 down to a shortlist of interesting candidates.

Fast, technical-only pass: bulk-fetch daily history through the cache, compute RSI / moving
averages / volume signals, filter for liquidity & data quality, then rank and take the top
15-25. Heavier per-stock work (fundamentals, Claude card) happens later on this shortlist.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ..data import cache

_UNIVERSE_PATH = Path(__file__).resolve().parent.parent / "data" / "nifty500_tickers.json"

# Filters / thresholds (from the build brief).
_MIN_AVG_VOLUME = 500_000      # liquid enough to trade
_MIN_HISTORY_DAYS = 60         # need enough bars for RSI + a 50-DMA
_RSI_OVERSOLD = 35
_RSI_OVERBOUGHT = 68
_VOLUME_SPIKE = 2.0            # today's vol vs 20-day avg
_MA_CROSS_WINDOW = 3          # "crossed 50-DMA in the last N trading days"

# A dev escape hatch: cap how many tickers we scan (cold runs over 500 are slow).
_SCAN_LIMIT = int(os.getenv("SIGNALS_SCAN_LIMIT", "0")) or None


def compute_rsi(prices: list[float], period: int = 14) -> float | None:
    """Most recent RSI (0-100) using Wilder smoothing. None if too few prices."""
    if len(prices) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    # Seed with the simple average of the first `period` changes.
    for i in range(1, period + 1):
        change = prices[i] - prices[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    # Wilder smoothing for the rest.
    for i in range(period + 1, len(prices)):
        change = prices[i] - prices[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def sma(prices: list[float], window: int) -> float | None:
    """Latest simple moving average over `window`, or None if too few prices."""
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def _crossed_above(closes: list[float], ma_window: int, lookback: int) -> bool:
    """True if price moved from below to above its MA within the last `lookback` days."""
    if len(closes) < ma_window + lookback:
        return False
    for i in range(1, lookback + 1):
        prev_ma = sma(closes[:-i], ma_window)
        cur_ma = sma(closes[: len(closes) - i + 1], ma_window)
        if prev_ma is None or cur_ma is None:
            continue
        prev_close = closes[-i - 1]
        cur_close = closes[-i]
        if prev_close < prev_ma and cur_close >= cur_ma:
            return True
    return False


def _load_universe() -> list[dict]:
    if not _UNIVERSE_PATH.exists():
        return []
    try:
        rows = json.loads(_UNIVERSE_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return rows[:_SCAN_LIMIT] if _SCAN_LIMIT else rows


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return round((a - b) / b * 100, 2)


def screen(limit: int = 20) -> list[dict]:
    """Return a ranked shortlist of candidate dicts with precomputed technicals."""
    universe = _load_universe()
    by_ticker = {row["ticker"]: row for row in universe}
    tickers = list(by_ticker)
    if not tickers:
        return []

    history = cache.bulk_download(tickers)
    candidates: list[dict] = []

    for ticker, bars in history.items():
        closes = [b["close"] for b in bars if b["close"] is not None]
        volumes = [b["volume"] for b in bars if b["volume"] is not None]
        if len(closes) < _MIN_HISTORY_DAYS or len(volumes) < 20:
            continue

        avg_vol_20 = sum(volumes[-20:]) / 20
        if avg_vol_20 < _MIN_AVG_VOLUME:
            continue

        rsi = compute_rsi(closes)
        if rsi is None:
            continue

        price = closes[-1]
        sma50 = sma(closes, 50)
        sma200 = sma(closes, 200)
        vs_50dma = _pct(price, sma50)
        vs_200dma = _pct(price, sma200)
        volume_ratio = round(volumes[-1] / avg_vol_20, 2) if avg_vol_20 else None
        week52_high = max(closes[-252:])
        week52_low = min(closes[-252:])
        change_today = _pct(price, closes[-2]) if len(closes) >= 2 else None
        cross_up = _crossed_above(closes, 50, _MA_CROSS_WINDOW)

        # Rank by how many notable signals fire (richer setups float to the top).
        rank = 0
        if rsi < _RSI_OVERSOLD or rsi > _RSI_OVERBOUGHT:
            rank += 1
        if cross_up:
            rank += 1
        if volume_ratio and volume_ratio >= _VOLUME_SPIKE:
            rank += 1
        if price <= week52_low * 1.05:
            rank += 1
        if price >= week52_high * 0.97:
            rank += 1
        if rank == 0:
            continue  # nothing interesting — skip

        row = by_ticker[ticker]
        candidates.append({
            "ticker": ticker,
            "display_name": row.get("name", ticker.split(".")[0]),
            "sector": row.get("sector", ""),
            "current_price": round(price, 2),
            "change_pct_today": change_today,
            "rsi": rsi,
            "vs_50dma": vs_50dma,
            "vs_200dma": vs_200dma,
            "volume_ratio": volume_ratio,
            "week52_high": round(week52_high, 2),
            "week52_low": round(week52_low, 2),
            "pct_from_52w_high": _pct(price, week52_high),
            "ma_cross_up": cross_up,
            "rank_score": rank,
        })

    candidates.sort(key=lambda c: c["rank_score"], reverse=True)
    return candidates[: max(limit, 0)]


if __name__ == "__main__":
    start = datetime.now(timezone.utc)
    out = screen()
    secs = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"Screened {len(out)} candidates in {secs:.1f}s")
    for c in out:
        print(f"  {c['ticker']:16} RSI {c['rsi']:5} vol×{c['volume_ratio']} "
              f"vs50 {c['vs_50dma']}% rank {c['rank_score']}")
