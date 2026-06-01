"""Company overview — AI-generated when a key is present, Yahoo's own blurb otherwise.

This is the single AI touchpoint in the stock page. It must always succeed:
- With ``ANTHROPIC_API_KEY``: ask ``OVERVIEW_MODEL`` for a clean 3-paragraph summary
  (prompt caching on the static system prompt), cached on disk for 7 days.
- Without a key: return yfinance's ``longBusinessSummary`` verbatim, flagged
  ``ai_generated: false``. No cost, no failure.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

from .. import config
from .cache import retry_with_backoff

_CACHE_DIR = config.DB_DIR / "overviews"
_CACHE_TTL = timedelta(days=7)

_SYSTEM_PROMPT = (
    "You are StockBrain's company-profile writer. Given raw company information, write a "
    "clean, neutral 3-paragraph overview for an investor: (1) what the company does, "
    "(2) its competitive position, (3) key things an investor should know. Plain English, "
    "no hype, no price predictions, no investment advice. Output only the three paragraphs."
)


def _info(ticker: str) -> dict:
    try:
        return retry_with_backoff(lambda: yf.Ticker(ticker).info) or {}
    except Exception:  # noqa: BLE001
        return {}


def _base_fields(info: dict) -> dict:
    return {
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "employees": info.get("fullTimeEmployees"),
        "website": info.get("website"),
        "country": info.get("country"),
        "founded": None,  # yfinance has no reliable founding-year field.
        "description_raw": info.get("longBusinessSummary", "") or "",
    }


def _cache_path(ticker: str) -> Path:
    safe = ticker.replace("/", "_")
    return _CACHE_DIR / f"{safe}.json"


def _read_cache(ticker: str) -> dict | None:
    path = _cache_path(ticker)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["_cached_at"])
        if datetime.now(timezone.utc) - cached_at < _CACHE_TTL:
            return data
    except (ValueError, OSError, KeyError):
        return None
    return None


def _write_cache(ticker: str, payload: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "_cached_at": datetime.now(timezone.utc).isoformat()}
    try:
        _cache_path(ticker).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # A failed cache write is non-fatal.


def _generate_ai_summary(info: dict) -> str | None:
    """Call Claude for a 3-paragraph summary. Returns None on any failure."""
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        facts = (
            f"Company: {info.get('longName') or info.get('shortName')}\n"
            f"Sector: {info.get('sector')}\nIndustry: {info.get('industry')}\n"
            f"Country: {info.get('country')}\nEmployees: {info.get('fullTimeEmployees')}\n"
            f"Website: {info.get('website')}\n\n"
            f"Yahoo business summary:\n{info.get('longBusinessSummary', '')}"
        )
        msg = client.messages.create(
            model=config.OVERVIEW_MODEL,
            max_tokens=600,
            system=[{
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # static across all tickers.
            }],
            messages=[{"role": "user", "content": facts}],
        )
        return "".join(block.text for block in msg.content if block.type == "text").strip()
    except Exception:  # noqa: BLE001 — fall back to the raw blurb on any API error.
        return None


def get_company_overview(ticker: str) -> dict:
    """Return ``{summary, ai_generated, sector, industry, employees, website, ...}``."""
    cached = _read_cache(ticker)
    if cached:
        cached.pop("_cached_at", None)
        return cached

    info = _info(ticker)
    base = _base_fields(info)

    summary = None
    ai_generated = False
    if config.has_anthropic_key():
        summary = _generate_ai_summary(info)
        ai_generated = summary is not None

    if not summary:
        # No key, or the API call failed — use Yahoo's own description.
        summary = base["description_raw"] or "No company overview available."

    result = {"summary": summary, "ai_generated": ai_generated, **base}

    # Only cache AI summaries (the raw-blurb path is already instant and free).
    if ai_generated:
        _write_cache(ticker, result)
    return result
