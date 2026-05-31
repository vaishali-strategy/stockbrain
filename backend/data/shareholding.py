"""Shareholding pattern — scraped from screener.in (yfinance has no Indian breakdown).

yfinance only exposes a generic insiders/institutions split, not the SEBI-style
Promoter / FII / DII / Government / Public pattern (with pledge) that Indian investors
expect. screener.in renders that table inline in the company page HTML, so we parse it
directly. Results are cached on disk for a day to avoid hammering screener.

This is the one source that intentionally steps outside yfinance, by explicit choice.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .cache import retry_with_backoff

_CACHE_DIR = Path(__file__).resolve().parent.parent / "db" / "shareholding"
_CACHE_TTL = timedelta(days=1)
_MAX_QUARTERS = 8  # keep the most recent N quarters for a tidy widget

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _symbol(ticker: str) -> str:
    """Strip the exchange suffix — screener keys companies by NSE symbol."""
    return ticker.split(".")[0].upper()


def _cache_path(symbol: str) -> Path:
    return _CACHE_DIR / f"{symbol}.json"


def _read_cache(symbol: str) -> dict | None:
    path = _cache_path(symbol)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
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
            json.dumps({**payload, "_cached_at": datetime.now(timezone.utc).isoformat()},
                       ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _to_pct(text: str) -> float | None:
    try:
        return round(float(text.replace("%", "").replace(",", "").strip()), 2)
    except (ValueError, AttributeError):
        return None


def _scrape(symbol: str) -> dict:
    """Parse the quarterly shareholding table from a screener.in company page."""

    def _fetch():
        resp = requests.get(
            f"https://www.screener.in/company/{symbol}/", headers=_HEADERS, timeout=20
        )
        resp.raise_for_status()
        return resp.text

    html = retry_with_backoff(_fetch)
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find(id="shareholding")
    if not section:
        return {"available": False, "source": "screener.in", "quarters": [], "categories": []}

    table = section.find("table")
    if not table or not table.find("thead"):
        return {"available": False, "source": "screener.in", "quarters": [], "categories": []}

    heads = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]
    quarters = heads[1:]  # first header cell is the row-label column

    categories: list[dict] = []
    shareholders: list = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if not cells:
            continue
        label = cells[0].rstrip("+").strip()  # screener appends "+" to expandable rows
        raw = cells[1:]
        if label.lower().startswith("no. of shareholders"):
            shareholders = raw[-_MAX_QUARTERS:]
            continue
        values = [_to_pct(c) for c in raw]
        categories.append({"label": label, "values": values[-_MAX_QUARTERS:]})

    return {
        "available": bool(categories),
        "source": "screener.in",
        "quarters": quarters[-_MAX_QUARTERS:],
        "categories": categories,
        "shareholders": shareholders,
    }


def get_shareholding(ticker: str) -> dict:
    """Return the quarterly shareholding pattern, cached for a day. Never raises."""
    symbol = _symbol(ticker)
    cached = _read_cache(symbol)
    if cached is not None:
        return cached
    try:
        result = _scrape(symbol)
    except Exception:  # noqa: BLE001 — scraping is best-effort; show "unavailable" on failure.
        result = {"available": False, "source": "screener.in", "quarters": [], "categories": []}
    if result.get("available"):
        _write_cache(symbol, result)
    return result
