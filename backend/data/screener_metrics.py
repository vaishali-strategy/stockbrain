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

from .. import config

_CACHE_DIR = config.DB_DIR / "screener_metrics"
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


def _find_return_row(soup: BeautifulSoup):
    """Locate the return-metric row. Banks report ROE (no ROCE), so accept either —
    preferring ROCE when both exist. Returns (metric, year_headers, values)."""
    found: dict[str, tuple] = {}
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if not thead:
            continue
        years = [th.get_text(strip=True) for th in thead.find_all("th")][1:]
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            label = _norm(cells[0].get_text())
            if label in ("roce", "roe") and label not in found:
                found[label] = (years, [_to_num(c.get_text()) for c in cells[1:]])
    for metric in ("roce", "roe"):
        if metric in found:
            return metric.upper(), found[metric][0], found[metric][1]
    return None, None, None


def _scrape(symbol: str) -> dict:
    def _fetch():
        r = requests.get(f"https://www.screener.in/company/{symbol}/", headers=_HEADERS, timeout=20)
        r.raise_for_status()
        return r.text

    soup = BeautifulSoup(retry_with_backoff(_fetch), "html.parser")
    metric, years, values = _find_return_row(soup)
    if not metric or not years or not values or all(v is None for v in values):
        return {"available": False, "source": "screener.in", "metric": None, "years": [], "roce": []}

    n = min(len(years), len(values))
    years, values = years[-n:], values[-n:]
    return {
        "available": True,
        "source": "screener.in",
        "metric": metric,  # "ROCE" for most firms, "ROE" for banks/financials
        "years": years[-10:],
        "roce": values[-10:],
    }


def get_roce_history(ticker: str) -> dict:
    """Return {available, metric, years[], roce[]} — ROCE (or ROE for banks). Never raises."""
    symbol = _symbol(ticker)
    cached = _read_cache(symbol)
    if cached is not None:
        return cached
    try:
        result = _scrape(symbol)
    except Exception:  # noqa: BLE001
        result = {"available": False, "source": "screener.in", "metric": None, "years": [], "roce": []}
    if result.get("available"):
        _write_cache(symbol, result)
    return result


# --------------------------------------------------------------------------- peers
def _peers_cache_path(symbol: str) -> Path:
    return _CACHE_DIR / f"{symbol}_peers.json"


def _read_peers_cache(symbol: str) -> dict | None:
    p = _peers_cache_path(symbol)
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


def _write_peers_cache(symbol: str, payload: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _peers_cache_path(symbol).write_text(
            json.dumps({**payload, "_cached_at": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _col_index(headers: list[str], *needles: str) -> int | None:
    """Find the column whose header contains any needle (case-insensitive)."""
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(n in hl for n in needles):
            return i
    return None


def _median(values: list[float]) -> float | None:
    vals = sorted(v for v in values if v is not None and v > 0)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    return round((vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2), 2)


def _scrape_peers(symbol: str) -> dict:
    empty = {"available": False, "source": "screener.in", "peers": []}

    def _fetch_page():
        r = requests.get(f"https://www.screener.in/company/{symbol}/", headers=_HEADERS, timeout=20)
        r.raise_for_status()
        return r.text

    page = retry_with_backoff(_fetch_page)
    m = re.search(r'data-warehouse-id="(\d+)"', page)
    if not m:
        return empty
    wid = m.group(1)

    def _fetch_peers():
        r = requests.get(
            f"https://www.screener.in/api/company/{wid}/peers/",
            headers={**_HEADERS, "Referer": f"https://www.screener.in/company/{symbol}/",
                     "X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        r.raise_for_status()
        return r.text

    soup = BeautifulSoup(retry_with_backoff(_fetch_peers), "html.parser")
    table = soup.find("table")
    if not table:
        return empty
    rows = table.find_all("tr")
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]

    i_name = _col_index(headers, "name")
    i_pe = _col_index(headers, "p/e", "pe")
    i_mcap = _col_index(headers, "mar cap", "market")
    i_dy = _col_index(headers, "div")
    i_roce = _col_index(headers, "roce")
    i_cmp = _col_index(headers, "cmp")
    if i_name is None or i_pe is None:
        return empty

    def cell(cells, idx):
        return cells[idx] if idx is not None and idx < len(cells) else ""

    peers: list[dict] = []
    median_row = None
    for tr in rows[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) <= i_pe:
            continue
        name = cell(cells, i_name)
        if name.lower().startswith("median"):
            median_row = {"pe": _to_num(cell(cells, i_pe)), "roce": _to_num(cell(cells, i_roce)),
                          "count": name}
            continue
        if not name:
            continue
        peers.append({
            "name": name,
            "pe": _to_num(cell(cells, i_pe)),
            "cmp": _to_num(cell(cells, i_cmp)),
            "market_cap": _to_num(cell(cells, i_mcap)),
            "dividend_yield": _to_num(cell(cells, i_dy)),
            "roce": _to_num(cell(cells, i_roce)),
        })

    if not peers:
        return empty

    # screener lists the subject company first.
    self_row = peers[0]
    others = peers[1:] if len(peers) > 1 else []
    median_pe = (median_row or {}).get("pe") or _median([p["pe"] for p in others or peers])
    median_roce = (median_row or {}).get("roce") or _median([p["roce"] for p in others or peers])

    return {
        "available": True,
        "source": "screener.in",
        "peers": peers,
        "self_name": self_row["name"],
        "self_pe": self_row["pe"],
        "self_roce": self_row["roce"],
        "median_pe": median_pe,
        "median_roce": median_roce,
    }


def get_peers(ticker: str) -> dict:
    """Return the screener.in peer-comparison table + peer-median P/E and ROCE. Never raises."""
    symbol = _symbol(ticker)
    cached = _read_peers_cache(symbol)
    if cached is not None:
        return cached
    try:
        result = _scrape_peers(symbol)
    except Exception:  # noqa: BLE001
        result = {"available": False, "source": "screener.in", "peers": []}
    if result.get("available"):
        _write_peers_cache(symbol, result)
    return result
