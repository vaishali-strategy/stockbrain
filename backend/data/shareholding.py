"""Shareholding pattern — scraped from screener.in (yfinance has no Indian breakdown).

Scraping is inherently fragile, so this module is built to **survive and detect** layout
changes rather than break silently:

- **Content-anchored location:** the shareholding table is found by its row *labels*
  (Promoters / FIIs / DIIs / Government / Public), not by the page's ``id``/CSS classes.
  That keeps working through most HTML/CSS redesigns.
- **Self-validation:** a parse is accepted only if it has the expected labels and the
  category percentages sum to ~100% per quarter. If validation fails, we flag
  ``structure_changed`` and **dump the fetched HTML** to ``backend/db/diagnostics/`` so the
  new structure can be inspected and the locator updated.

This is the one source that intentionally steps outside yfinance, by explicit choice.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .cache import retry_with_backoff

logger = logging.getLogger("stockbrain.shareholding")

from .. import config

_CACHE_DIR = config.DB_DIR / "shareholding"
_DIAG_DIR = config.DB_DIR / "diagnostics"
_CACHE_TTL = timedelta(days=1)
_MAX_QUARTERS = 8

# Known category labels — the stable content anchor. screener is very unlikely to rename
# these even in a redesign. Matching ≥3 identifies the right table regardless of markup.
_KNOWN_LABELS = {"promoters", "fiis", "diis", "government", "public"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# --------------------------------------------------------------------------- caching
def _symbol(ticker: str) -> str:
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


# --------------------------------------------------------------------------- helpers
def _norm(label: str) -> str:
    """Normalize a row label for matching: lowercase, drop screener's '+', strip punctuation."""
    return re.sub(r"[^a-z]", "", label.lower())


def _to_pct(text: str) -> float | None:
    try:
        return round(float(text.replace("%", "").replace(",", "").strip()), 2)
    except (ValueError, AttributeError):
        return None


def _table_label_score(table) -> int:
    """How many known category labels appear in this table's first column."""
    found = set()
    for tr in table.find_all("tr"):
        cell = tr.find(["td", "th"])
        if cell:
            n = _norm(cell.get_text())
            for known in _KNOWN_LABELS:
                if n.startswith(known):
                    found.add(known)
    return len(found)


def _find_shareholding_table(soup: BeautifulSoup):
    """Locate the shareholding table by content, with structure-based hints first.

    Returns (table, strategy_name) or (None, None).
    """
    # Hint 1: the historical id (fast path when markup is unchanged).
    section = soup.find(id="shareholding")
    if section:
        t = section.find("table")
        if t and _table_label_score(t) >= 3:
            return t, "id=shareholding"

    # Hint 2: a heading mentioning shareholding, then its following table.
    for heading in soup.find_all(["h1", "h2", "h3"]):
        if "shareholding" in heading.get_text(strip=True).lower():
            t = heading.find_next("table")
            if t and _table_label_score(t) >= 3:
                return t, "heading-anchored"

    # Hint 3 (fully content-anchored): scan every table, pick the best label match.
    best, best_score = None, 0
    for t in soup.find_all("table"):
        score = _table_label_score(t)
        if score > best_score:
            best, best_score = t, score
    if best is not None and best_score >= 3:
        return best, "content-scan"

    return None, None


def _parse_table(table) -> dict:
    """Parse a located table into quarters + category rows. Generic to row/header layout."""
    rows = table.find_all("tr")
    if not rows:
        return {"quarters": [], "categories": [], "shareholders": []}

    # Header = first row whose cells (after the label col) look like period labels.
    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    quarters = header_cells[1:]

    categories: list[dict] = []
    shareholders: list = []
    for tr in rows[1:]:
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        label = cells[0].rstrip("+").strip()
        raw = cells[1:]
        if "shareholder" in _norm(label):
            shareholders = raw[-_MAX_QUARTERS:]
            continue
        values = [_to_pct(c) for c in raw]
        if any(v is not None for v in values):
            categories.append({"label": label, "values": values[-_MAX_QUARTERS:]})

    return {
        "quarters": quarters[-_MAX_QUARTERS:],
        "categories": categories,
        "shareholders": shareholders,
    }


def _validate(parsed: dict) -> tuple[bool, str]:
    """Sanity-check a parse. Returns (ok, reason)."""
    cats = parsed.get("categories", [])
    labels = {_norm(c["label"]) for c in cats}
    known_hits = sum(1 for k in _KNOWN_LABELS if any(l.startswith(k) for l in labels))
    if known_hits < 3:
        return False, f"only {known_hits} known category labels found"
    if not parsed.get("quarters"):
        return False, "no quarter columns parsed"

    # Percentages for the most recent quarter should sum to ~100%.
    idx = len(parsed["quarters"]) - 1
    total = sum(
        c["values"][idx]
        for c in cats
        if idx < len(c["values"]) and c["values"][idx] is not None
    )
    if not (90 <= total <= 110):
        return False, f"category percentages sum to {total:.1f}% (expected ~100%)"
    return True, "ok"


def _dump_diagnostic(symbol: str, html: str, reason: str) -> None:
    """Persist the fetched HTML when parsing breaks, so the new layout can be found."""
    _DIAG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        (_DIAG_DIR / f"shareholding_{symbol}_{stamp}.html").write_text(html, encoding="utf-8")
    except OSError:
        pass
    logger.warning(
        "screener.in shareholding parse failed for %s (%s). "
        "HTML snapshot saved to %s for inspection.",
        symbol, reason, _DIAG_DIR,
    )


def _empty(reason: str, changed: bool) -> dict:
    return {
        "available": False,
        "source": "screener.in",
        "structure_ok": not changed,
        "structure_changed": changed,
        "reason": reason,
        "quarters": [],
        "categories": [],
    }


# --------------------------------------------------------------------------- public API
def _scrape(symbol: str) -> dict:
    def _fetch():
        resp = requests.get(
            f"https://www.screener.in/company/{symbol}/", headers=_HEADERS, timeout=20
        )
        resp.raise_for_status()
        return resp.text

    html = retry_with_backoff(_fetch)
    soup = BeautifulSoup(html, "html.parser")

    table, strategy = _find_shareholding_table(soup)
    if table is None:
        _dump_diagnostic(symbol, html, "no table matched known category labels")
        return _empty("table not found", changed=True)

    parsed = _parse_table(table)
    ok, reason = _validate(parsed)
    if not ok:
        _dump_diagnostic(symbol, html, reason)
        return _empty(reason, changed=True)

    if strategy != "id=shareholding":
        # We still found it, but not via the expected anchor — worth noting.
        logger.info("shareholding for %s located via fallback strategy '%s'", symbol, strategy)

    return {
        "available": True,
        "source": "screener.in",
        "structure_ok": True,
        "structure_changed": False,
        "strategy": strategy,
        **parsed,
    }


def get_shareholding(ticker: str) -> dict:
    """Return the quarterly shareholding pattern, cached for a day. Never raises.

    On a screener.in layout change, returns ``available: false`` with
    ``structure_changed: true`` and leaves an HTML snapshot in db/diagnostics/.
    """
    symbol = _symbol(ticker)
    cached = _read_cache(symbol)
    if cached is not None:
        return cached
    try:
        result = _scrape(symbol)
    except Exception as exc:  # noqa: BLE001 — network/parse errors degrade gracefully.
        logger.warning("shareholding fetch error for %s: %s", symbol, exc)
        result = _empty(f"fetch error: {exc}", changed=False)
    if result.get("available"):
        _write_cache(symbol, result)
    return result
