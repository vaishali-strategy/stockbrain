"""Query the persisted vault collection by semantic similarity (+ metadata filters)."""

from __future__ import annotations

from . import embedder


def is_empty() -> bool:
    """True when the vault has not been indexed (or has no chunks)."""
    try:
        return embedder.get_collection().count() == 0
    except Exception:  # noqa: BLE001
        return True


def stats() -> dict:
    """Total chunks and distinct source files currently indexed."""
    try:
        col = embedder.get_collection()
        total = col.count()
        if total == 0:
            return {"total_chunks": 0, "total_notes": 0}
        meta = col.get(include=["metadatas"]).get("metadatas", []) or []
        sources = {m.get("source") for m in meta if m}
        return {"total_chunks": total, "total_notes": len(sources)}
    except Exception:  # noqa: BLE001
        return {"total_chunks": 0, "total_notes": 0}


def retrieve(query: str, filters: dict | None = None, k: int = 6) -> list[dict]:
    """Return up to k relevant chunks as {page_content, metadata, distance}."""
    if is_empty() or not query.strip():
        return []
    col = embedder.get_collection()
    try:
        res = col.query(
            query_embeddings=embedder.embed_texts([query]),
            n_results=k,
            where=filters or None,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:  # noqa: BLE001
        return []

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out = []
    for i, text in enumerate(docs):
        out.append({
            "page_content": text,
            "metadata": metas[i] if i < len(metas) else {},
            "distance": dists[i] if i < len(dists) else None,
        })
    return out
