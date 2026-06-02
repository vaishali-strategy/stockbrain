"""Portfolio-wide analysis: a fundamental good/watch/weak verdict + news impact per holding.

Reuses the per-stock engines (``data.quality`` for fundamentals, ``data.news`` +
``data.news_impact`` for news). The heavy work — screener.in scraping + yfinance + one LLM
call per holding — runs concurrently in threads behind a small semaphore, and is cached per
ticker so re-runs are instant. Holdings arrive from the client (they live in browser
localStorage), so this module is stateless about *what* the user owns.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from .. import config
from . import llm, news, news_impact, quality

_IST = timezone(timedelta(hours=5, minutes=30))
_CACHE_PATH = config.DB_DIR / "portfolio_analysis_cache.json"
_FUND_TTL = timedelta(hours=24)   # fundamentals move slowly
_NEWS_TTL = timedelta(hours=4)    # news is fresher
_CONCURRENCY = 4                  # be polite to screener.in / yfinance
_LLM_CEILING = int(os.getenv("PORTFOLIO_MAX_LLM_CALLS", "25"))  # per-run budget guard

_lock = asyncio.Lock()


# --------------------------------------------------------------------------- verdict
def _verdict(q: dict) -> dict:
    """Band quality.py's existing pass/warn/fail checklist into good/watch/weak.

    No new scoring math — we only band the score quality.py already produces, so the
    per-stock ProfitabilityAnalysis view and this portfolio view stay consistent.
    """
    checklist = q.get("checklist", [])
    score = q.get("checklist_score", 0)
    total = q.get("checklist_total", 0) or 1
    ratio = score / total
    fails = sum(1 for c in checklist if c.get("status") == "fail")
    if ratio >= 0.65 and fails <= 1:
        verdict = "good"
    elif ratio < 0.40 or fails >= 3:
        verdict = "weak"
    else:
        verdict = "watch"
    concerns = [
        {"label": c["label"], "detail": c["detail"]}
        for c in checklist if c.get("status") in ("fail", "warn")
    ][:3]
    strengths = [
        {"label": c["label"], "detail": c["detail"]}
        for c in checklist if c.get("status") == "pass"
    ][:2]
    return {
        "verdict": verdict,
        "score": score,
        "total": q.get("checklist_total", 0),
        "strengths": strengths,
        "concerns": concerns,
        "narrative": q.get("narrative", ""),
    }


# --------------------------------------------------------------------------- cache
def _read_cache() -> dict:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


async def _write_cache(data: dict) -> None:
    async with _lock:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def _fresh(entry: dict, key: str, ttl: timedelta) -> bool:
    sub = entry.get(key)
    if not isinstance(sub, dict) or "_at" not in sub:
        return False
    try:
        at = datetime.fromisoformat(sub["_at"])
    except (ValueError, TypeError):
        return False
    return datetime.now(timezone.utc) - at < ttl


# --------------------------------------------------------------------------- per ticker
def _analyze_one(ticker: str, name: str, cached: dict, force: bool, use_llm: bool) -> dict:
    """Blocking: compute (or reuse from cache) the fundamental verdict + news impact."""
    now = datetime.now(timezone.utc).isoformat()
    entry = dict(cached) if cached else {}

    if force or not _fresh(entry, "fundamental", _FUND_TTL):
        try:
            q = quality.get_quality_analysis(ticker)
            entry["fundamental"] = {**_verdict(q), "_at": now}
        except Exception:  # noqa: BLE001
            entry.setdefault("fundamental", {
                "verdict": "watch", "score": 0, "total": 0,
                "strengths": [], "concerns": [], "narrative": "", "_at": now,
            })

    if force or not _fresh(entry, "news", _NEWS_TTL):
        try:
            heads = news.get_news(ticker, 4)
            entry["news"] = {**news_impact.assess(ticker, name, heads, use_llm=use_llm), "_at": now}
        except Exception:  # noqa: BLE001
            entry.setdefault("news", {
                "stance": "neutral", "rationale": "News unavailable.",
                "actionable": False, "engine": "none", "top": [], "_at": now,
            })
    return entry


# --------------------------------------------------------------------------- run
async def analyze(holdings: list[dict], force: bool = False) -> dict:
    """Analyze every holding; return buckets + a 'news to watch' list. See module docstring."""
    cache = _read_cache()
    sem = asyncio.Semaphore(_CONCURRENCY)
    # Only the first N holdings (by request order) may use the LLM, so a large portfolio
    # can't blow the API budget; the rest fall back to the keyword heuristic for news.
    order = {h.get("ticker"): i for i, h in enumerate(holdings)}

    async def _run(h: dict) -> tuple[str, dict]:
        ticker = h.get("ticker")
        name = h.get("name") or ticker.split(".")[0]
        use_llm = order.get(ticker, 10**9) < _LLM_CEILING
        async with sem:
            entry = await asyncio.to_thread(
                _analyze_one, ticker, name, cache.get(ticker, {}), force, use_llm
            )
        return ticker, entry

    for ticker, entry in await asyncio.gather(*[_run(h) for h in holdings]):
        cache[ticker] = entry
    await _write_cache(cache)

    holdings_out: list[dict] = []
    buckets: dict[str, list[str]] = {"good": [], "watch": [], "weak": []}
    news_to_watch: list[str] = []
    for h in holdings:
        ticker = h.get("ticker")
        name = h.get("name") or ticker.split(".")[0]
        entry = cache.get(ticker, {})
        fund = {k: v for k, v in entry.get("fundamental", {}).items() if k != "_at"}
        nws = {k: v for k, v in entry.get("news", {}).items() if k != "_at"}
        holdings_out.append({"ticker": ticker, "name": name, "fundamental": fund, "news": nws})
        buckets.setdefault(fund.get("verdict", "watch"), []).append(ticker)
        if nws.get("actionable"):
            news_to_watch.append(ticker)

    return {
        "analyzed_at": datetime.now(_IST).isoformat(),
        "engine": llm.active_engine() or "heuristic",
        "holdings": holdings_out,
        "buckets": buckets,
        "news_to_watch": news_to_watch,
    }
