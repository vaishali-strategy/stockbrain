"""On-disk daily OHLCV cache + the shared yfinance retry helper.

yfinance against NSE/BSE (``.NS``/``.BO``) rate-limits aggressively, and the signals
screener (later pass) needs ~500 tickers per run. So every history read goes through this
cache: callers read from SQLite, and we only hit the network when a ticker's data is
missing or stale. ``retry_with_backoff`` is the single retry wrapper used everywhere a
yfinance call happens.
"""

from __future__ import annotations

import random
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, TypeVar

import yfinance as yf

_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "ohlcv_cache.sqlite"

# A ticker's cached history is considered fresh for this long before we refetch.
_FRESH_TTL = timedelta(hours=6)

# How much daily history we cache per ticker (covers the longest chart period, 1Y).
_HISTORY_PERIOD = "1y"

# Map a UI chart period to a lookback window in calendar days (we slice cached rows).
_PERIOD_DAYS = {"1w": 7, "1mo": 31, "3mo": 93, "6mo": 186, "1y": 372}

# All-time history is fetched weekly (not daily) to keep the payload light, and memoized
# in-process for a few hours since it changes slowly and the toggle is used rarely.
_MAX_TTL = timedelta(hours=6)
_max_memo: dict[str, tuple[datetime, list[dict]]] = {}

T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[..., T],
    *args,
    retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> T:
    """Call ``fn`` with exponential backoff + jitter. Re-raises after the last attempt.

    Used to wrap every yfinance call so transient rate-limits don't surface as errors.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — yfinance raises many ad-hoc error types.
            last_exc = exc
            if attempt < retries - 1:
                delay = base_delay * (2**attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ohlcv (
            ticker TEXT NOT NULL,
            date   TEXT NOT NULL,
            open   REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (ticker, date)
        )
        """
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (ticker TEXT PRIMARY KEY, last_fetched TEXT)"
    )
    return conn


def _is_fresh(conn: sqlite3.Connection, ticker: str) -> bool:
    row = conn.execute("SELECT last_fetched FROM meta WHERE ticker = ?", (ticker,)).fetchone()
    if not row:
        return False
    try:
        last = datetime.fromisoformat(row[0])
    except (TypeError, ValueError):
        return False
    return datetime.now(timezone.utc) - last < _FRESH_TTL


def _fetch_and_store(conn: sqlite3.Connection, ticker: str) -> None:
    """Fetch ~1y of daily history from yfinance (with retry) and upsert into the cache."""

    def _download():
        return yf.Ticker(ticker).history(period=_HISTORY_PERIOD, interval="1d", auto_adjust=False)

    df = retry_with_backoff(_download)
    if df is None or df.empty:
        # Mark as fetched anyway so we don't hammer the network for a dead ticker.
        conn.execute(
            "INSERT OR REPLACE INTO meta (ticker, last_fetched) VALUES (?, ?)",
            (ticker, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return

    rows = [
        (
            ticker,
            idx.strftime("%Y-%m-%d"),
            _num(r.get("Open")),
            _num(r.get("High")),
            _num(r.get("Low")),
            _num(r.get("Close")),
            _num(r.get("Volume")),
        )
        for idx, r in df.iterrows()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (ticker, last_fetched) VALUES (?, ?)",
        (ticker, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def _num(value) -> float | None:
    """Coerce a pandas/numpy scalar to a plain float, or None if missing/NaN."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check


def _get_max_history(ticker: str) -> list[dict]:
    """All-time weekly OHLCV (memoized ~6h). Fetched straight from yfinance, not the cache."""
    memo = _max_memo.get(ticker)
    if memo and datetime.now(timezone.utc) - memo[0] < _MAX_TTL:
        return memo[1]

    def _download():
        return yf.Ticker(ticker).history(period="max", interval="1wk", auto_adjust=False)

    try:
        df = retry_with_backoff(_download)
    except Exception:  # noqa: BLE001
        return memo[1] if memo else []
    if df is None or df.empty:
        return memo[1] if memo else []

    rows = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "open": _num(r.get("Open")), "high": _num(r.get("High")),
            "low": _num(r.get("Low")), "close": _num(r.get("Close")),
            "volume": _num(r.get("Volume")),
        }
        for idx, r in df.iterrows()
    ]
    _max_memo[ticker] = (datetime.now(timezone.utc), rows)
    return rows


def get_history(ticker: str, period: str = "3mo") -> list[dict]:
    """Return OHLCV for ``ticker`` over ``period`` as a list of dicts (oldest first).

    Daily periods read from the on-disk cache; ``max``/``all`` returns weekly all-time data.
    Returns ``[]`` if data can't be obtained.
    """
    period = period.lower()
    if period in ("max", "all"):
        return _get_max_history(ticker)
    window_days = _PERIOD_DAYS.get(period, _PERIOD_DAYS["3mo"])
    conn = _connect()
    try:
        if not _is_fresh(conn, ticker):
            _fetch_and_store(conn, ticker)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d")
        cur = conn.execute(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker = ? AND date >= ? ORDER BY date ASC",
            (ticker, cutoff),
        )
        return [
            {
                "date": d,
                "open": o,
                "high": h,
                "low": low,
                "close": c,
                "volume": v,
            }
            for (d, o, h, low, c, v) in cur.fetchall()
        ]
    finally:
        conn.close()


def bulk_download(tickers: list[str]) -> dict[str, list[dict]]:
    """Bulk-fetch daily history for many tickers in one yfinance call (screener path).

    Used later by the Nifty-500 screener — never loop one ticker at a time over 500 names.
    One bad ticker is skipped, not fatal. Results are also written to the cache.
    """
    if not tickers:
        return {}

    def _download():
        return yf.download(
            tickers, period=_HISTORY_PERIOD, interval="1d",
            group_by="ticker", auto_adjust=False, progress=False, threads=True,
        )

    data = retry_with_backoff(_download)
    out: dict[str, list[dict]] = {}
    # With group_by="ticker" and many symbols, columns are a MultiIndex keyed by ticker.
    cols = getattr(data, "columns", None)
    multi = hasattr(cols, "levels")
    available = set(cols.get_level_values(0)) if multi else set()
    conn = _connect()
    try:
        for ticker in tickers:
            try:
                if multi:
                    if ticker not in available:
                        continue
                    sub = data[ticker]
                else:
                    sub = data  # single-ticker download → flat columns
                if sub is None or sub.empty:
                    continue
                rows = [
                    (ticker, idx.strftime("%Y-%m-%d"), _num(r.get("Open")), _num(r.get("High")),
                     _num(r.get("Low")), _num(r.get("Close")), _num(r.get("Volume")))
                    for idx, r in sub.iterrows()
                ]
                conn.executemany(
                    "INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
                conn.execute(
                    "INSERT OR REPLACE INTO meta (ticker, last_fetched) VALUES (?, ?)",
                    (ticker, datetime.now(timezone.utc).isoformat()),
                )
                out[ticker] = [
                    {"date": r[1], "open": r[2], "high": r[3], "low": r[4],
                     "close": r[5], "volume": r[6]}
                    for r in rows
                ]
            except Exception:  # noqa: BLE001 — skip a bad ticker, never break the run.
                continue
        conn.commit()
    finally:
        conn.close()
    return out
