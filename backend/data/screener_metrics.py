"""Scrape long-horizon ratios from screener.in — currently the 10-year ROCE history.

yfinance only carries ~4 years of statements, but the moat test the framework calls for
needs a *decade* of ROCE to judge consistency. screener.in renders that in its Ratios
table, so we parse it the same content-anchored way as the shareholding scraper (find the
row by its label, not by fragile CSS), and cache for a day.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .cache import retry_with_backoff

_CACHE_DIR = Path(__file__).resolve().parent.parent / "db" / "screener_metrics"
_CACHE_TTL = timedelta(days=1)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _symbol(ticker: str) -> str:
    return ticker.split(".")[0].upper()


def _cache_path(symbol: str) -> Path:
    return _CACHE_DIR / f"{symbol}.json"


def _read_cache(symbol: str) -> dict | None:
    p = _cache_path(symbol)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if datetime.now(timezone.utc) - datetime.fromisoformat(data["_cached_at"]) < _CACHE_TTL:
            data.pop("_cached_at", None)
            return data
    except (ValueError, OSError, KeyError):
        return None
    return None


def _write_cache(symbol: str, payload: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _cache_path(symbol).write_text(
            json.dumps({**payload, "_cached_at": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _norm(label: str) -> str:
    return re.sub(r"[^a-z]", "", label.lower())


def _to_num(text: str) -> float | None:
    try:
        return round(float(text.replace("%", "").replace(",", "").strip()), 2)
    except (ValueError, AttributeError):
        return None


def _find_roce_row(soup: BeautifulSoup):
    """Return (year_headers, roce_values) by locating the table row labelled ROCE."""
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if not thead:
            continue
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            if _norm(cells[0].get_text()) == "roce":
                years = [th.get_text(strip=True) for th in thead.find_all("th")][1:]
                values = [_to_num(c.get_text()) for c in cells[1:]]
                return years, values
    return None, None


def _scrape(symbol: str) -> dict:
    def _fetch():
        r = requests.get(f"https://www.screener.in/company/{symbol}/", headers=_HEADERS, timeout=20)
        r.raise_for_status()
        return r.text

    soup = BeautifulSoup(retry_with_backoff(_fetch), "html.parser")
    years, values = _find_roce_row(soup)
    if not years or not values or all(v is None for v in values):
        return {"available": False, "source": "screener.in", "years": [], "roce": []}

    # Align lengths and keep the most recent ~10 years.
    n = min(len(years), len(values))
    years, values = years[-n:], values[-n:]
    return {
        "available": True,
        "source": "screener.in",
        "years": years[-10:],
        "roce": values[-10:],
    }


def get_roce_history(ticker: str) -> dict:
    """Return {available, years[], roce[]} for the ROCE % history. Never raises."""
    symbol = _symbol(ticker)
    cached = _read_cache(symbol)
    if cached is not None:
        return cached
    try:
        result = _scrape(symbol)
    except Exception:  # noqa: BLE001
        result = {"available": False, "source": "screener.in", "years": [], "roce": []}
    if result.get("available"):
        _write_cache(symbol, result)
    return result
