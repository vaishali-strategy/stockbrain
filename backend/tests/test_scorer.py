"""Unit tests for the pure RSI + signal/confidence logic (no network)."""

from __future__ import annotations

from backend.signals import scorer, screener


# --------------------------------------------------------------------------- RSI
def test_rsi_all_gains_is_100():
    prices = [float(i) for i in range(1, 30)]  # strictly rising
    assert screener.compute_rsi(prices) == 100.0


def test_rsi_too_few_prices_is_none():
    assert screener.compute_rsi([1.0, 2.0, 3.0]) is None


def test_rsi_midrange_for_choppy_series():
    # Alternating up/down should land RSI somewhere in the middle, not at an extreme.
    prices = []
    p = 100.0
    for i in range(40):
        p += 1.0 if i % 2 == 0 else -1.0
        prices.append(p)
    rsi = screener.compute_rsi(prices)
    assert rsi is not None and 30 < rsi < 70


# --------------------------------------------------------------------------- signal type
def test_buy_when_oversold_above_ma_cheap():
    assert scorer.classify_signal(rsi=30, vs_50dma=-3, pe_ratio=22, pct_from_52w_high=-12) == "BUY"


def test_buy_allowed_when_pe_unknown():
    assert scorer.classify_signal(rsi=30, vs_50dma=-3, pe_ratio=None, pct_from_52w_high=-12) == "BUY"


def test_not_buy_when_pe_too_high():
    assert scorer.classify_signal(rsi=30, vs_50dma=-3, pe_ratio=55, pct_from_52w_high=-12) != "BUY"


def test_sell_when_overbought_extended_near_high():
    assert scorer.classify_signal(rsi=72, vs_50dma=8, pe_ratio=30, pct_from_52w_high=-2) == "SELL"


def test_watch_is_the_default():
    assert scorer.classify_signal(rsi=50, vs_50dma=1, pe_ratio=20, pct_from_52w_high=-20) == "WATCH"


# --------------------------------------------------------------------------- confidence
def test_high_confidence_with_three_signals():
    cand = {
        "rsi": 30,                 # oversold
        "volume_ratio": 2.5,       # volume spike
        "ma_cross_up": True,       # momentum
        "current_price": 100,
        "week52_low": 200,
        "week52_high": 400,
    }
    assert scorer.classify_confidence(cand) == "HIGH"


def test_medium_confidence_with_two_signals():
    cand = {
        "rsi": 30,                 # oversold
        "volume_ratio": 2.5,       # volume spike
        "ma_cross_up": False,
        "current_price": 300,
        "week52_low": 200,
        "week52_high": 400,
    }
    assert scorer.classify_confidence(cand) == "MEDIUM"


def test_low_confidence_with_one_signal():
    cand = {
        "rsi": 30,                 # oversold only
        "volume_ratio": 1.0,
        "ma_cross_up": False,
        "current_price": 300,
        "week52_low": 200,
        "week52_high": 400,
    }
    assert scorer.classify_confidence(cand) == "LOW"


def test_near_52w_support_counts_as_signal():
    cand = {
        "rsi": 50,
        "volume_ratio": 1.0,
        "ma_cross_up": False,
        "current_price": 204,      # within 5% of the 52w low (200)
        "week52_low": 200,
        "week52_high": 400,
    }
    assert scorer.classify_confidence(cand) == "LOW"  # exactly one signal
