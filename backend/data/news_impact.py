"""Assess whether a holding's recent news is bullish/bearish for an existing shareholder.

LLM path (Claude/Ollama via ``data.llm``) reads the headlines and returns a one-line
stance; keyless/offline it falls back to a small keyword lexicon. News sentiment is
otherwise absent from the app — this is the only place it is computed.
"""

from __future__ import annotations

import json
import re

from .. import config
from . import llm

_SYSTEM = (
    "You assess recent news for someone who ALREADY OWNS shares of an Indian (NSE/BSE) "
    "stock. Decide whether the news, on balance, is bullish, bearish, or neutral for the "
    "holder, and explain why in ONE short sentence. Hedge ('may', 'suggests'); never "
    "guarantee; name the key risk. Respond with ONLY compact JSON, no markdown: "
    '{"stance":"bullish|bearish|neutral","rationale":"<one sentence>"}.'
)

# Coarse keyword lexicon for the keyless/offline fallback. Honest but blunt.
_BEARISH = (
    "downgrade", "cut", "miss", "missed", "probe", "fraud", "scam", "lawsuit", "fine",
    "penalty", "resign", "slump", "plunge", "fall", "drop", "loss", "weak", "warning",
    "raid", "default", "stake sale", "block deal", "ban", "recall", "decline", "sell-off",
)
_BULLISH = (
    "beat", "beats", "upgrade", "record", "surge", "jump", "rally", "order win",
    "deal win", "bags order", "wins order", "expansion", "approval", "approved",
    "buyback", "profit rise", "strong", "outperform", "acquire", "all-time high",
)


def _heuristic(headlines: list[dict]) -> dict:
    text = " ".join((h.get("title") or "").lower() for h in headlines)
    bull = sum(1 for w in _BULLISH if w in text)
    bear = sum(1 for w in _BEARISH if w in text)
    if bull > bear:
        return {"stance": "bullish", "rationale": "Recent headlines skew positive (keyword scan)."}
    if bear > bull:
        return {"stance": "bearish", "rationale": "Recent headlines skew negative (keyword scan)."}
    return {"stance": "neutral", "rationale": "No clear directional signal in recent headlines."}


def _parse_llm(raw: str) -> dict | None:
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        obj = json.loads(m.group(0) if m else raw)
        stance = str(obj.get("stance", "")).lower()
        if stance not in ("bullish", "bearish", "neutral"):
            return None
        return {"stance": stance, "rationale": str(obj.get("rationale", "")).strip()}
    except (ValueError, AttributeError, TypeError):
        return None


def assess(ticker: str, name: str, headlines: list[dict], *, use_llm: bool = True) -> dict:
    """Return {stance, rationale, actionable, engine, top}. Never raises.

    ``use_llm=False`` forces the heuristic (used when a run hits the LLM budget ceiling).
    ``actionable`` is True only for bullish/bearish — neutral is hidden from "News to watch".
    """
    top = [
        {"title": h.get("title", ""), "url": h.get("url", ""), "source": h.get("source", "")}
        for h in headlines[:3]
    ]
    if not headlines:
        return {"stance": "neutral", "rationale": "No recent news.",
                "actionable": False, "engine": "none", "top": top}

    result = None
    engine = "heuristic"
    if use_llm:
        lines = "\n".join(f"- {h.get('title', '')} ({h.get('source', '')})" for h in headlines[:6])
        raw = llm.complete(
            _SYSTEM,
            f"Stock: {name} ({ticker})\nRecent headlines:\n{lines}",
            model=config.SIGNALS_MODEL,  # cheap, high-volume — same model as signal cards
            max_tokens=160,
        )
        if raw:
            result = _parse_llm(raw)
            if result:
                engine = llm.active_engine() or "heuristic"
    if not result:
        result = _heuristic(headlines)

    return {
        "stance": result["stance"],
        "rationale": result["rationale"],
        "actionable": result["stance"] in ("bullish", "bearish"),
        "engine": engine,
        "top": top,
    }
