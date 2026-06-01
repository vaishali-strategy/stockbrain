"""RAG chat orchestration: gather context, then stream a grounded answer.

Static instructions live in the (prompt-cached) system prompt; the per-request vault +
market context goes in the user turn so the cache actually helps. Streaming uses the
Anthropic SDK directly. Works with no vault (skips retrieval) — the no-API-key path is
handled by the chat API, which composes a reply from retrieved snippets instead.
"""

from __future__ import annotations

from .. import config
from ..data import market, news
from . import retriever

_SYSTEM_PROMPT = """You are StockBrain, an expert stock market research assistant.

You have access to the user's private Obsidian research vault — their personal notes, \
investment theses, earnings observations, and watchlists. Treat this as ground truth for \
their views and research.

You also have access to live market data and recent news.

When answering:
- Always cite which note or source you're drawing from (e.g. "From your NVDA thesis note...")
- Distinguish clearly between the user's own research and external data
- Be direct about uncertainty — if the vault doesn't have information on something, say so
- Never fabricate financial data. If you don't have a number, say you don't have it.
- Format responses with clear headers when answering multi-part questions
- These are Indian stocks (NSE/BSE); prices are in ₹. This is research, not investment advice."""


def _market_context(ticker: str | None) -> str:
    if not ticker:
        return "(no specific ticker in context)"
    q = market.get_quote(ticker)
    if q.get("error"):
        return f"{ticker}: live data unavailable."
    line = (
        f"{ticker}: ₹{q.get('price')} ({q.get('change_pct')}% today), "
        f"P/E {q.get('pe_ratio')}, 52w ₹{q.get('week52_low')}–₹{q.get('week52_high')}."
    )
    heads = news.get_news(ticker, 2)
    if heads:
        line += " Recent news: " + "; ".join(h["title"] for h in heads if h.get("title"))
    return line


def _format_vault(chunks: list[dict]) -> tuple[str, list[dict]]:
    if not chunks:
        return "(no relevant notes found in your vault)", []
    blocks = []
    sources: list[dict] = []
    seen = set()
    for c in chunks:
        m = c.get("metadata", {})
        fname = m.get("filename", "note")
        label = fname
        if m.get("ticker"):
            label += f" · {m['ticker']}"
        blocks.append(f"From note '{label}' (type: {m.get('type', 'note')}):\n{c['page_content']}")
        key = m.get("source", fname)
        if key not in seen:
            seen.add(key)
            sources.append({
                "filename": fname,
                "ticker": m.get("ticker"),
                "type": m.get("type"),
            })
    return "\n\n---\n\n".join(blocks), sources


def build_context(query: str, ticker_context: str | None = None) -> dict:
    """Retrieve vault chunks + live market data. Returns {vault_text, market_text, sources}."""
    chunks = retriever.retrieve(query, k=6)
    vault_text, sources = _format_vault(chunks)
    return {
        "vault_text": vault_text,
        "market_text": _market_context(ticker_context),
        "sources": sources,
        "used_vault": bool(chunks),
    }


def _user_turn(query: str, context: dict) -> str:
    return (
        f"Vault context:\n{context['vault_text']}\n\n"
        f"Live market data:\n{context['market_text']}\n\n"
        f"User question: {query}"
    )


def stream_tokens(query: str, context: dict, history: list[dict] | None = None):
    """Yield answer text deltas from Claude (caller must ensure an API key is set)."""
    from anthropic import Anthropic

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    messages = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": _user_turn(query, context)})

    with client.messages.stream(
        model=config.CHAT_MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
