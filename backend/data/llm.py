"""Shared one-shot LLM completion with the app's standard provider fallback.

Routes the same way chat does: Anthropic (when a key is set) → local Ollama → None.
A caller that gets ``None`` falls back to its own rule-based template, so every feature
keeps working keyless and offline. This is the non-streaming sibling of ``rag/chain.py``
(which streams); both share the same provider-selection logic.
"""

from __future__ import annotations

import time

import requests

from .. import config

# Cache the local-Ollama reachability probe briefly so we don't hit it on every call.
_ollama_state: tuple[float, bool] = (0.0, False)


def ollama_available() -> bool:
    global _ollama_state
    ts, ok = _ollama_state
    if time.time() - ts < 30:
        return ok
    try:
        ok = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=2).status_code == 200
    except Exception:  # noqa: BLE001
        ok = False
    _ollama_state = (time.time(), ok)
    return ok


def active_engine() -> str | None:
    """Which engine ``complete()`` would use right now: 'claude', 'ollama', or None.

    Mirrors ``rag.chain.resolve_provider`` but reports the user-facing engine name.
    """
    p = config.get_llm_provider()
    if p == "anthropic":
        return "claude" if config.has_anthropic_key() else None
    if p == "ollama":
        return "ollama" if ollama_available() else None
    # auto: prefer Claude when a key exists, else fall back to a local model.
    if config.has_anthropic_key():
        return "claude"
    if ollama_available():
        return "ollama"
    return None


def complete(system: str, user: str, *, model: str, max_tokens: int = 256) -> str | None:
    """One-shot completion via the active engine. Returns None if no engine / on error.

    The system prompt is prompt-cached on the Anthropic path — callers reuse one system
    string across many items (e.g. per-holding news), so the cache actually helps.
    """
    engine = active_engine()
    if engine == "claude":
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in msg.content if b.type == "text").strip() or None
        except Exception:  # noqa: BLE001 — caller falls back to its template.
            return None
    if engine == "ollama":
        try:
            resp = requests.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": config.get_ollama_model(),
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                },
                timeout=(10, 300),  # local generation can be slow to first token
            )
            resp.raise_for_status()
            return ((resp.json().get("message") or {}).get("content") or "").strip() or None
        except Exception:  # noqa: BLE001
            return None
    return None
