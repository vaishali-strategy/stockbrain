"""Streaming RAG chat endpoint.

Degrades gracefully on two axes:
- No vault / empty index → answer from live data + model knowledge, nudge to connect a vault.
- No Anthropic key → can't write a model answer, so return the relevant note snippets we
  retrieved (retrieval is local/free) plus a clear nudge to add a key. Never errors.

Responses are Server-Sent Events: each line is `data: {json}\n\n`.
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import config
from ..rag import chain, retriever

router = APIRouter(tags=["chat"])


class ChatIn(BaseModel):
    message: str
    ticker_context: str | None = None
    conversation_history: list[dict] = []


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@router.post("/chat")
def chat(req: ChatIn):
    context = chain.build_context(req.message, req.ticker_context)
    has_key = config.has_anthropic_key()
    vault_empty = retriever.is_empty()

    def gen():
        if has_key:
            try:
                for token in chain.stream_tokens(req.message, context, req.conversation_history):
                    yield _sse({"token": token, "done": False})
            except Exception as exc:  # noqa: BLE001
                yield _sse({"token": f"\n\n[Error contacting the model: {exc}]", "done": False})
            # A gentle nudge when the vault could have helped but isn't there.
            if vault_empty:
                yield _sse({
                    "token": "\n\n💡 Connect your Obsidian vault to include your personal research in answers.",
                    "done": False,
                })
        else:
            # No key: surface what retrieval found (free/local) instead of a model answer.
            if context["used_vault"]:
                msg = "🔑 Add an Anthropic API key to get full conversational answers. "
                msg += "Meanwhile, here are the most relevant notes from your vault:\n\n"
                for s in context["sources"]:
                    tag = f" ({s['ticker']})" if s.get("ticker") else ""
                    msg += f"• {s['filename']}{tag}\n"
            elif vault_empty:
                msg = (
                    "🔑 Add an Anthropic API key to chat with live data and AI, and connect your "
                    "Obsidian vault to bring your own research into answers."
                )
            else:
                msg = "🔑 Add an Anthropic API key (console.anthropic.com) to enable AI answers."
            yield _sse({"token": msg, "done": False})

        yield _sse({
            "token": "",
            "done": True,
            "sources": context["sources"],
            "used_vault": context["used_vault"],
            "ai_generated": has_key,
        })

    return StreamingResponse(gen(), media_type="text/event-stream")
