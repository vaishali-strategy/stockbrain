"""Chunk, embed (local ONNX via fastembed), and persist vault notes to ChromaDB.

- Embeddings are computed locally with fastembed — free, offline, no torch, no OpenAI.
- Indexing is incremental: a file is re-embedded only when its mtime changes, and its old
  chunks are deleted before the new ones are added (so re-syncing never duplicates chunks).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .. import config
from . import loader

# chromadb is imported lazily inside get_collection() so the server can start even if the
# (heavy) vector-store dependency isn't present/loaded yet — only RAG sync/search needs it.

_COLLECTION = "stockbrain_vault"
_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 100

_embedder = None  # lazy fastembed model
_client = None    # lazy chroma client


def _state_path() -> Path:
    return Path(config.CHROMA_PATH).resolve().parent / "vault_index_state.json"


def _load_state() -> dict:
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def _save_state(state: dict) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding

        _embedder = TextEmbedding(model_name=config.EMBED_MODEL)
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in get_embedder().embed(texts)]


def get_collection():
    global _client
    if _client is None:
        import chromadb  # lazy: heavy native dep, only needed for vault indexing/search

        Path(config.CHROMA_PATH).resolve().mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(Path(config.CHROMA_PATH).resolve()))
    return _client.get_or_create_collection(_COLLECTION, metadata={"hnsw:space": "cosine"})


def _split_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Char-window chunks with overlap, preferring a clean break near the window end."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        if end >= len(text):
            # Final window — take the remainder and stop (prevents tiny tail chunks).
            tail = chunk.strip()
            if tail:
                chunks.append(tail)
            break
        # Prefer a clean break point in the back half of the window.
        for sep in ("\n\n", "\n", ". ", " "):
            idx = chunk.rfind(sep)
            if idx > size * 0.5:
                chunk = chunk[: idx + len(sep)]
                break
        stripped = chunk.strip()
        if stripped:
            chunks.append(stripped)
        start += max(len(chunk) - overlap, size // 2)  # always advance meaningfully
    return chunks


def _index_doc(collection, doc: dict) -> int:
    """(Re)index a single loaded doc. Deletes its old chunks first. Returns chunk count."""
    source = doc["metadata"]["source"]
    collection.delete(where={"source": source})  # delete-before-add → no stale duplicates

    chunks = _split_text(doc["page_content"])
    if not chunks:
        return 0
    ids = [f"{source}::{i}" for i in range(len(chunks))]
    metadatas = [{**doc["metadata"], "chunk_index": i} for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embed_texts(chunks),
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def index_vault(vault_path: str) -> dict:
    """Incrementally (re)index a whole vault. Returns {files_indexed, chunks_created}."""
    docs = loader.load_vault(vault_path)
    collection = get_collection()
    state = _load_state()

    seen_sources = set()
    files_indexed = 0
    chunks_created = 0

    for doc in docs:
        source = doc["metadata"]["source"]
        seen_sources.add(source)
        try:
            mtime = os.path.getmtime(source)
        except OSError:
            mtime = None
        if state.get(source) == mtime:
            continue  # unchanged since last sync
        chunks_created += _index_doc(collection, doc)
        state[source] = mtime
        files_indexed += 1

    # Drop notes deleted from the vault since the last sync.
    for stale in [s for s in state if s not in seen_sources]:
        collection.delete(where={"source": stale})
        state.pop(stale, None)

    _save_state(state)
    return {"files_indexed": files_indexed, "chunks_created": chunks_created}


def embed_single_file(file_path: str) -> bool:
    """Index one note immediately (used right after saving via the notes API)."""
    doc = loader.load_file(file_path)
    if not doc:
        return False
    _index_doc(get_collection(), doc)
    state = _load_state()
    try:  # key by the same `source` used during a full sync, so mtimes stay consistent
        state[doc["metadata"]["source"]] = os.path.getmtime(doc["metadata"]["source"])
    except OSError:
        pass
    _save_state(state)
    return True
