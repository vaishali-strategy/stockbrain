"""Technical analysis engine.

Computes the standard technical toolkit (trend, momentum, volatility, levels, volume and
candlestick patterns) from daily OHLCV, and synthesizes an overall bull/bear rating — the
same families of indicators taught in introductory TA courses (e.g. Zerodha Varsity). All
maths is implemented here from first principles; no TA library is added.
"""

from __future__ import annotations

from .cache import get_history


# --------------------------------------------------------------------------- primitives
def _sma(vals: list[float], n: int) -> float | None:
    return sum(vals[-n:]) / n if len(vals) >= n else None


def _ema_series(vals: list[float], n: int) -> list[float]:
    """Full EMA series (seeded with the SMA of the first n values)."""
    if len(vals) < n:
        return []
    k = 2 / (n + 1)
    ema = sum(vals[:n]) / n
    out = [ema]
    for v in vals[n:]:
        ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def _ema(vals: list[float], n: int) -> float | None:
    s = _ema_series(vals, n)
    return s[-1] if s else None


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        gains += max(ch, 0.0)
        losses += max(-ch, 0.0)
    ag, al = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(ch, 0.0)) / period
        al = (al * (period - 1) + max(-ch, 0.0)) / period
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 2)


def _macd(closes: list[float]):
    """Return (macd, signal, histogram) for the standard 12/26/9 setup."""
    e12, e26 = _ema_series(closes, 12), _ema_series(closes, 26)
    if not e12 or not e26:
        return None, None, None
    # Align the two EMA series (e12 starts earlier) to the same tail length.
    n = min(len(e12), len(e26))
    macd_series = [a - b for a, b in zip(e12[-n:], e26[-n:])]
    sig_series = _ema_series(macd_series, 9)
    if not sig_series:
        return round(macd_series[-1], 2), None, None
    macd, signal = macd_series[-1], sig_series[-1]
    return round(macd, 2), round(signal, 2), round(macd - signal, 2)


def _stochastic(highs, lows, closes, k: int = 14, d: int = 3):
    if len(closes) < k + d:
        return None, None
    k_series = []
    for i in range(k - 1, len(closes)):
        hh = max(highs[i - k + 1 : i + 1])
        ll = min(lows[i - k + 1 : i + 1])
        k_series.append(100 * (closes[i] - ll) / (hh - ll) if hh != ll else 50.0)
    pct_k = k_series[-1]
    pct_d = sum(k_series[-d:]) / d
    return round(pct_k, 2), round(pct_d, 2)


def _atr(highs, lows, closes, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 2)


def _adx(highs, lows, closes, period: int = 14):
    """Return (adx, plus_di, minus_di) using Wilder smoothing."""
    n = len(closes)
    if n < 2 * period + 1:
        return None, None, None
    trs, plus_dm, minus_dm = [], [], []
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if (up > down and up > 0) else 0.0)
        minus_dm.append(down if (down > up and down > 0) else 0.0)
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))

    def _wilder(vals):
        s = sum(vals[:period])
        out = [s]
        for v in vals[period:]:
            s = s - s / period + v
            out.append(s)
        return out

    tr_s, p_s, m_s = _wilder(trs), _wilder(plus_dm), _wilder(minus_dm)
    dx = []
    for tr, p, m in zip(tr_s, p_s, m_s):
        if tr == 0:
            dx.append(0.0)
            continue
        pdi, mdi = 100 * p / tr, 100 * m / tr
        dx.append(100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0.0)
    if len(dx) < period:
        return None, None, None
    adx = sum(dx[:period]) / period
    for v in dx[period:]:
        adx = (adx * (period - 1) + v) / period
    pdi = 100 * p_s[-1] / tr_s[-1] if tr_s[-1] else 0.0
    mdi = 100 * m_s[-1] / tr_s[-1] if tr_s[-1] else 0.0
    return round(adx, 2), round(pdi, 2), round(mdi, 2)


def _obv_trend(closes, volumes) -> str | None:
    if len(closes) < 20:
        return None
    obv = 0.0
    series = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i] or 0
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i] or 0
        series.append(obv)
    return "rising" if series[-1] > series[-20] else "falling"


# --------------------------------------------------------------------------- assembly
def _signal(value, bull, bear):
    """Map a value to bullish/bearish/neutral given oversold/overbought-style bounds."""
    if value is None:
        return "neutral"
    if bull(value):
        return "bullish"
    if bear(value):
        return "bearish"
    return "neutral"


def get_technical_analysis(ticker: str) -> dict:
    bars = get_history(ticker, "1y")
    closes = [b["close"] for b in bars if b["close"] is not None]
    highs = [b["high"] for b in bars if b["high"] is not None]
    lows = [b["low"] for b in bars if b["low"] is not None]
    vols = [b["volume"] for b in bars if b["volume"] is not None]
    if len(closes) < 60:
        return {"available": False}

    price = closes[-1]
    last = bars[-1]
    prev = bars[-2] if len(bars) >= 2 else None

    # --- Moving averages (trend) ---
    ma_defs = [("SMA 20", _sma(closes, 20)), ("SMA 50", _sma(closes, 50)),
               ("SMA 100", _sma(closes, 100)), ("SMA 200", _sma(closes, 200)),
               ("EMA 20", _ema(closes, 20)), ("EMA 50", _ema(closes, 50))]
    moving_averages = []
    for name, val in ma_defs:
        if val is None:
            continue
        moving_averages.append({
            "name": name, "value": round(val, 2),
            "signal": "bullish" if price > val else "bearish",
        })
    sma50, sma200 = _sma(closes, 50), _sma(closes, 200)
    cross = None
    if sma50 and sma200:
        cross = "golden cross (50 > 200)" if sma50 > sma200 else "death cross (50 < 200)"

    # --- Oscillators (momentum) ---
    rsi = _rsi(closes)
    k, d = _stochastic(highs, lows, closes)
    macd, macd_sig, macd_hist = _macd(closes)
    adx, pdi, mdi = _adx(highs, lows, closes)
    mom = round(price - closes[-11], 2) if len(closes) >= 11 else None  # 10-day momentum

    oscillators = [
        {"name": "RSI (14)", "value": rsi,
         "signal": _signal(rsi, lambda v: v < 30, lambda v: v > 70),
         "note": "Oversold < 30, overbought > 70"},
        {"name": "Stochastic %K (14,3)", "value": k,
         "signal": _signal(k, lambda v: v < 20, lambda v: v > 80),
         "note": "Oversold < 20, overbought > 80"},
        {"name": "MACD (12,26,9)", "value": macd,
         "signal": "bullish" if (macd is not None and macd_sig is not None and macd > macd_sig)
                   else "bearish" if macd is not None else "neutral",
         "note": f"Signal {macd_sig}, histogram {macd_hist}"},
        {"name": "Momentum (10d)", "value": mom,
         "signal": _signal(mom, lambda v: v > 0, lambda v: v < 0),
         "note": "Price change over 10 sessions"},
        {"name": "ADX (14)", "value": adx,
         "signal": ("bullish" if (pdi or 0) > (mdi or 0) else "bearish") if (adx or 0) >= 20 else "neutral",
         "note": f"+DI {pdi} / −DI {mdi}; trend {'strong' if (adx or 0) >= 25 else 'weak'} (ADX {adx})"},
    ]

    # --- Bollinger Bands (volatility) ---
    bb = None
    mid = _sma(closes, 20)
    if mid is not None and len(closes) >= 20:
        window = closes[-20:]
        std = (sum((c - mid) ** 2 for c in window) / 20) ** 0.5
        upper, lower = mid + 2 * std, mid - 2 * std
        pb = (price - lower) / (upper - lower) if upper != lower else 0.5
        bb = {
            "upper": round(upper, 2), "middle": round(mid, 2), "lower": round(lower, 2),
            "percent_b": round(pb * 100, 1),
            "signal": "bearish" if pb > 1 else "bullish" if pb < 0 else "neutral",
        }
    atr = _atr(highs, lows, closes)

    # --- Levels: 52w, pivots, fib, swing S/R ---
    w52_high, w52_low = max(closes[-252:]), min(closes[-252:])
    pos = round((price - w52_low) / (w52_high - w52_low) * 100, 1) if w52_high != w52_low else None
    ph, pl, pc = last["high"], last["low"], last["close"]
    pp = (ph + pl + pc) / 3
    pivots = {
        "PP": round(pp, 2),
        "R1": round(2 * pp - pl, 2), "S1": round(2 * pp - ph, 2),
        "R2": round(pp + (ph - pl), 2), "S2": round(pp - (ph - pl), 2),
        "R3": round(ph + 2 * (pp - pl), 2), "S3": round(pl - 2 * (ph - pp), 2),
    }
    swing_hi, swing_lo = max(highs[-63:]), min(lows[-63:])  # ~3 months
    diff = swing_hi - swing_lo
    fib = [{"level": lv, "price": round(swing_hi - diff * lv / 100, 2)}
           for lv in (23.6, 38.2, 50, 61.8, 78.6)] if diff else []
    # nearest recent support/resistance from swing structure
    resistance = round(swing_hi, 2)
    support = round(swing_lo, 2)

    # --- Candlestick pattern (latest, with one lookback for engulfing) ---
    candle = _candlestick(last, prev, closes)

    # --- Overall rating tally ---
    bull = bear = neutral = 0
    for grp in (moving_averages, oscillators):
        for it in grp:
            if it["signal"] == "bullish":
                bull += 1
            elif it["signal"] == "bearish":
                bear += 1
            else:
                neutral += 1
    rating = _rating_label(bull, bear)

    return {
        "available": True,
        "as_of": last["date"],
        "price": round(price, 2),
        "rating": {"label": rating, "bullish": bull, "bearish": bear, "neutral": neutral},
        "moving_averages": moving_averages,
        "ma_cross": cross,
        "oscillators": oscillators,
        "bollinger": bb,
        "atr": atr,
        "trend": {"adx": adx, "plus_di": pdi, "minus_di": mdi,
                  "strength": "strong" if (adx or 0) >= 25 else "weak"},
        "volume": {"avg_20": round(sum(vols[-20:]) / 20) if len(vols) >= 20 else None,
                   "ratio": round(vols[-1] / (sum(vols[-20:]) / 20), 2) if len(vols) >= 20 and sum(vols[-20:]) else None,
                   "obv_trend": _obv_trend(closes, vols)},
        "levels": {"week52_high": round(w52_high, 2), "week52_low": round(w52_low, 2),
                   "position_pct": pos, "support": support, "resistance": resistance,
                   "pivots": pivots, "fibonacci": fib},
        "candlestick": candle,
    }


def _rating_label(bull: int, bear: int) -> str:
    total = bull + bear
    if total == 0:
        return "Neutral"
    score = (bull - bear) / total
    if score >= 0.5:
        return "Strong Buy"
    if score >= 0.2:
        return "Buy"
    if score <= -0.5:
        return "Strong Sell"
    if score <= -0.2:
        return "Sell"
    return "Neutral"


def _candlestick(last, prev, closes) -> dict | None:
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]
    if None in (o, h, l, c):
        return None
    rng = h - l
    if rng == 0:
        return None
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    downtrend = len(closes) >= 6 and closes[-1] < closes[-6]
    uptrend = len(closes) >= 6 and closes[-1] > closes[-6]

    def res(name, implication):
        return {"pattern": name, "implication": implication}

    # Engulfing (needs the previous candle)
    if prev and None not in (prev["open"], prev["close"]):
        po, pc = prev["open"], prev["close"]
        if c > o and pc < po and c >= po and o <= pc:
            return res("Bullish Engulfing", "A green candle fully engulfs the prior red one — potential bullish reversal.")
        if c < o and pc > po and o >= pc and c <= po:
            return res("Bearish Engulfing", "A red candle fully engulfs the prior green one — potential bearish reversal.")

    if body <= 0.1 * rng:
        return res("Doji", "Open ≈ close — indecision; watch for a follow-through move.")
    if lower >= 2 * body and upper <= body and downtrend:
        return res("Hammer", "Long lower wick after a fall — buyers stepped in; potential bullish reversal.")
    if upper >= 2 * body and lower <= body and uptrend:
        return res("Shooting Star", "Long upper wick after a rise — sellers stepped in; potential bearish reversal.")
    if body >= 0.9 * rng:
        return res("Marubozu", f"Full-body {'green' if c > o else 'red'} candle — strong {'buying' if c > o else 'selling'} conviction.")
    return None
