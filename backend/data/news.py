"""Recent news for a ticker.

Uses NewsAPI.org when ``NEWS_API_KEY`` is configured, otherwise yfinance's built-in news
feed (free, no key). Always returns a list of uniform dicts; never raises.
"""

from __future__ import annotations

from datetime import datetime, timezone

import requests
import yfinance as yf

from .. import config
from .cache import retry_with_backoff


def _from_newsapi(ticker: str, limit: int) -> list[dict]:
    # Strip the exchange suffix for a cleaner news query.
    query = ticker.split(".")[0]
    resp = requests.get(
        "https://newsapi.org/v2/everything",
        params={"q": query, "sortBy": "publishedAt", "pageSize": limit, "language": "en"},
        headers={"X-Api-Key": config.NEWS_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    return [
        {
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": a.get("publishedAt", ""),
            "summary": a.get("description", "") or "",
        }
        for a in articles[:limit]
    ]


def _from_yfinance(ticker: str, limit: int) -> list[dict]:
    raw = retry_with_backoff(lambda: yf.Ticker(ticker).news) or []
    out: list[dict] = []
    for item in raw[:limit]:
        # yfinance nests fields under "content" in newer versions; fall back to flat keys.
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
            "title": title,
            "url": url,
            "source": source,
            "published_at": pub or "",
            "summary": content.get("summary", "") or "",
        })
    return out


def _epoch_to_iso(epoch) -> str:
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return ""


def get_news(ticker: str, limit: int = 5) -> list[dict]:
    """Return up to ``limit`` recent news items for ``ticker``."""
    try:
        if config.NEWS_API_KEY:
            return _from_newsapi(ticker, limit)
        return _from_yfinance(ticker, limit)
    except Exception:  # noqa: BLE001 — news is non-critical; never break the stock page.
        return []
