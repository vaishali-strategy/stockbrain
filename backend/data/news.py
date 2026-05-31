"""Recent news for a ticker.

Source priority:
1. NewsAPI.org      — if NEWS_API_KEY is set (richest, keyed)
2. Google News RSS  — free, no key, India-aware (hl=en-IN); the default source
3. yfinance news    — last-resort fallback

Google News is queried by company *name* (not the raw symbol) for far better
relevance on Indian stocks. Always returns a uniform list; never raises.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import requests
import yfinance as yf

from .. import config
from . import search
from .cache import retry_with_backoff

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _rfc822_to_iso(text: str) -> str:
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return ""


def _from_newsapi(ticker: str, limit: int) -> list[dict]:
    query = search.company_name(ticker)
    resp = requests.get(
        "https://newsapi.org/v2/everything",
        params={"q": query, "sortBy": "publishedAt", "pageSize": limit, "language": "en"},
        headers={"X-Api-Key": config.NEWS_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": a.get("publishedAt", ""),
            "summary": a.get("description", "") or "",
        }
        for a in resp.json().get("articles", [])[:limit]
    ]


def _from_google_news(ticker: str, limit: int) -> list[dict]:
    """Parse Google News RSS for the company. Free, no key, India-localized."""
    name = search.company_name(ticker)
    # "<Company> share price" biases results toward market/finance coverage.
    query = quote_plus(f"{name} share price")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    def _fetch():
        r = requests.get(url, headers=_HEADERS, timeout=12)
        r.raise_for_status()
        return r.content

    root = ET.fromstring(retry_with_backoff(_fetch))
    out: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = _rfc822_to_iso(item.findtext("pubDate") or "")
        # <source> holds the publisher; Google also suffixes " - Publisher" onto the title.
        src_el = item.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if not source and " - " in title:
            source = title.rsplit(" - ", 1)[-1].strip()
        # Trim the trailing " - Publisher" Google appends to titles.
        if source and title.endswith(f" - {source}"):
            title = title[: -(len(source) + 3)].strip()
        out.append({
            "title": title,
            "url": link,
            "source": source,
            "published_at": pub,
            "summary": "",  # Google News descriptions are noisy aggregations — omit.
        })
        if len(out) >= limit:
            break
    return out


def _from_yfinance(ticker: str, limit: int) -> list[dict]:
    raw = retry_with_backoff(lambda: yf.Ticker(ticker).news) or []
    out: list[dict] = []
    for item in raw[:limit]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title", "")
        url = (
            (content.get("canonicalUrl") or {}).get("url")
            or content.get("link")
            or item.get("link", "")
        )
        provider = content.get("provider") or {}
        source = provider.get("displayName") or item.get("publisher", "")
        pub = content.get("pubDate") or _epoch_to_iso(item.get("providerPublishTime"))
        out.append({
            "title": title, "url": url, "source": source,
            "published_at": pub or "", "summary": content.get("summary", "") or "",
        })
    return out


def _epoch_to_iso(epoch) -> str:
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return ""


def get_news(ticker: str, limit: int = 5) -> list[dict]:
    """Return up to ``limit`` recent news items, trying sources in priority order."""
    if config.NEWS_API_KEY:
        try:
            items = _from_newsapi(ticker, limit)
            if items:
                return items
        except Exception:  # noqa: BLE001 — fall through to the free sources.
            pass

    try:
        items = _from_google_news(ticker, limit)
        if items:
            return items
    except Exception:  # noqa: BLE001
        pass

    try:
        return _from_yfinance(ticker, limit)
    except Exception:  # noqa: BLE001
        return []
