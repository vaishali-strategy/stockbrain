"""Generate a plain-English signal card per candidate and orchestrate a full run.

With an Anthropic key: each card is written by SIGNALS_MODEL (Haiku) — cheap, high-volume,
with prompt caching on the shared system prompt and a per-run ceiling so a refresh can never
blow the budget. Without a key: a deterministic template is used (still honest, hedged, and
always names a risk). Results are cached to signals_cache.json for 4 hours.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import config
from . import scorer, screener

_CACHE_PATH = Path(__file__).resolve().parent.parent / "db" / "signals_cache.json"
_CACHE_TTL = timedelta(hours=4)
_IST = timezone(timedelta(hours=5, minutes=30))

_MAX_CANDIDATES = 20
_CLAUDE_CEILING = int(os.getenv("SIGNALS_MAX_CLAUDE_CALLS", "25"))  # budget guard
_CONCURRENCY = 5

_SYSTEM_PROMPT = (
    "You are StockBrain's stock analyst. You analyze Indian stocks listed on NSE/BSE.\n\n"
    "Your job: given structured data about a stock, write a concise, honest signal card that "
    "helps a retail investor decide whether to investigate further.\n\n"
    "Rules:\n"
    "- Write in plain English. No jargon unless explained.\n"
    "- Be direct. If the signal is weak, say so.\n"
    "- Never guarantee returns. Never say \"will go up\" or \"guaranteed\". Use \"suggests\", "
    "\"indicates\", \"may\".\n"
    "- Always mention at least one risk, even for strong BUY signals.\n"
    "- Keep the entire output under 120 words.\n"
    "- Output only the analysis text — no headers, no bullet points, no markdown."
)

# Shared run state (read by GET /signals/status). Mutations are guarded by _lock.
_progress: dict = {"running": False, "message": "Idle", "done": 0, "total": 0}
_lock = asyncio.Lock()


# --------------------------------------------------------------------------- progress
async def _set_progress(**kwargs) -> None:
    async with _lock:
        _progress.update(kwargs)


def get_progress() -> dict:
    return dict(_progress)


# --------------------------------------------------------------------------- cache
def read_cache() -> dict | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def cache_age_minutes() -> int | None:
    data = read_cache()
    if not data or "generated_at" not in data:
        return None
    try:
        gen = datetime.fromisoformat(data["generated_at"])
    except ValueError:
        return None
    return int((datetime.now(_IST) - gen).total_seconds() // 60)


def _is_fresh() -> bool:
    age = cache_age_minutes()
    return age is not None and age < _CACHE_TTL.total_seconds() / 60


async def _write_cache(payload: dict) -> None:
    async with _lock:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            _CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


# --------------------------------------------------------------------------- card text
def _template_card(s: dict) -> str:
    """Deterministic, hedged signal text used without a key or beyond the Claude budget."""
    verb = {
        "BUY": "may suggest early accumulation interest",
        "SELL": "may indicate profit-taking risk",
        "WATCH": "warrants monitoring for now",
    }[s["signal_type"]]
    return (
        f"{s['display_name']} {verb}. {s['technicals_summary']}. {s['fundamentals_summary']}. "
        f"This is a {s['confidence'].lower()}-confidence {s['signal_type']} signal. "
        "Key risk: technical setups can fail in a weak broader market — confirm with your own "
        "research before acting. Not investment advice."
    )


def _user_prompt(s: dict) -> str:
    vault_line = (
        "User has personal research notes on this stock." if s.get("vault_has_notes") else ""
    )
    return (
        f"Stock: {s['display_name']} ({s['ticker']}) — {s['sector']}\n"
        f"Signal: {s['signal_type']} | Confidence: {s['confidence']}\n"
        f"Price: ₹{s['current_price']} | Change today: {s['change_pct_today']}%\n"
        f"RSI (14): {s['rsi']} | vs 50-DMA: {s['vs_50dma']}% | vs 200-DMA: {s['vs_200dma']}%\n"
        f"Volume ratio: {s['volume_ratio']}x average\n"
        f"P/E: {s['pe_ratio']} | Net margin: {s['net_margin']}% | "
        f"Revenue growth YoY: {s['revenue_growth_yoy']}%\n"
        f"52-week range: ₹{s['week52_low']} – ₹{s['week52_high']} "
        f"(currently {s['pct_from_52w_high']}% from high)\n"
        f"Technicals: {s['technicals_summary']}\n"
        f"Fundamentals: {s['fundamentals_summary']}\n"
        f"{vault_line}\n\n"
        "Write a concise signal analysis (under 120 words)."
    )


async def _claude_card(client, s: dict) -> str:
    msg = await client.messages.create(
        model=config.SIGNALS_MODEL,
        max_tokens=256,
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # identical across all candidates
        }],
        messages=[{"role": "user", "content": _user_prompt(s)}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


# --------------------------------------------------------------------------- run
async def run(force: bool = False) -> dict:
    """Screen → score → analyze the Nifty 500 and cache the result. Returns the payload."""
    if not force and _is_fresh():
        return read_cache()
    if _progress["running"]:
        return read_cache() or {"signals": [], "generated_at": None}

    await _set_progress(running=True, message="Scanning Nifty 500…", done=0, total=0)
    try:
        # Screening + scoring are blocking (network) → offload to threads.
        candidates = await asyncio.to_thread(screener.screen, _MAX_CANDIDATES)
        await _set_progress(message=f"Scoring {len(candidates)} candidates…", total=len(candidates))

        scores: list[dict] = []
        for i, cand in enumerate(candidates):
            scores.append(await asyncio.to_thread(scorer.score_candidate, cand))
            await _set_progress(done=i + 1, message=f"Scoring {i + 1}/{len(candidates)}…")

        await _set_progress(message="Generating analysis…", done=0, total=len(scores))
        use_claude = config.has_anthropic_key()
        client = None
        if use_claude:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

        sem = asyncio.Semaphore(_CONCURRENCY)
        done_count = 0

        async def _analyze(idx: int, s: dict) -> None:
            nonlocal done_count
            text = None
            if use_claude and idx < _CLAUDE_CEILING:  # honor the per-run budget cap
                try:
                    async with sem:
                        text = await _claude_card(client, s)
                except Exception:  # noqa: BLE001 — fall back to the template on any API error.
                    text = None
            s["analysis"] = text or _template_card(s)
            done_count += 1
            await _set_progress(done=done_count, message=f"Generating {done_count}/{len(scores)}…")

        await asyncio.gather(*[_analyze(i, s) for i, s in enumerate(scores)])

        payload = {
            "signals": scores,
            "generated_at": datetime.now(_IST).isoformat(),
            "total_candidates_scanned": screener.universe_size(),
            "signals_returned": len(scores),
            "ai_generated": use_claude,
        }
        await _write_cache(payload)
        return payload
    finally:
        await _set_progress(running=False, message="Done")
