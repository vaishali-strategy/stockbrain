"""Save notes into the vault and list a ticker's notes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import frontmatter
from fastapi import APIRouter
from pydantic import BaseModel

from .. import config
from ..rag import embedder, loader

router = APIRouter(tags=["notes"])

# note_type → (vault subfolder, frontmatter `type`)
_FOLDERS = {
    "company": ("Companies", "company"),
    "earnings": ("Earnings", "earnings"),
    "thesis": ("Thesis", "thesis"),
    "news": ("News", "news"),
    "journal": ("Journal", "journal"),
}


class NoteIn(BaseModel):
    ticker: str = ""
    note_type: str = "company"
    content: str = ""
    frontmatter: dict = {}


def _unique_path(folder: Path, stem: str) -> Path:
    """Return folder/stem.md, or stem_2.md, stem_3.md… so we never overwrite a note."""
    candidate = folder / f"{stem}.md"
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem}_{n}.md"
        n += 1
    return candidate


@router.post("/notes")
def save_note(note: NoteIn) -> dict:
    vault = config.get_vault_path()
    if not vault or not Path(vault).expanduser().is_dir():
        return {"error": "No vault configured. Set a vault folder first.", "indexed": False}

    subfolder, fm_type = _FOLDERS.get(note.note_type, _FOLDERS["company"])
    folder = Path(vault).expanduser() / subfolder
    folder.mkdir(parents=True, exist_ok=True)

    ticker = (note.ticker or "").upper().strip()
    if note.note_type == "journal":
        stem = f"journal_{date.today().isoformat()}"
    elif note.note_type == "company":
        stem = ticker or "note"
    else:
        stem = f"{ticker}_{note.note_type}" if ticker else note.note_type
    path = _unique_path(folder, stem)

    # Assemble frontmatter: caller-provided values + sensible defaults.
    meta = {
        "type": fm_type,
        "date": date.today().isoformat(),
        **({"ticker": ticker} if ticker else {}),
        **(note.frontmatter or {}),
    }
    post = frontmatter.Post(note.content or "", **meta)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")

    indexed = False
    try:
        indexed = embedder.embed_single_file(str(path))
    except Exception:  # noqa: BLE001 — saving must succeed even if indexing hiccups.
        indexed = False

    return {"path": str(path), "indexed": indexed}


@router.get("/notes/{ticker}")
def notes_for_ticker(ticker: str) -> dict:
    """List vault notes that reference this ticker (by frontmatter or filename)."""
    vault = config.get_vault_path()
    if not vault or not Path(vault).expanduser().is_dir():
        return {"ticker": ticker, "notes": []}

    target = ticker.split(".")[0].upper()
    out = []
    for doc in loader.load_vault(vault):
        m = doc["metadata"]
        hay = f"{m.get('ticker', '')} {m.get('tickers', '')} {m.get('filename', '')}".upper()
        if target in hay:
            out.append({
                "filename": m.get("filename"),
                "path": m.get("source"),
                "type": m.get("type"),
                "snippet": doc["page_content"][:160],
            })
    return {"ticker": ticker, "notes": out}
