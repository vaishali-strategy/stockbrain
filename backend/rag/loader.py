"""Load an Obsidian vault into plain documents for embedding.

Walks the vault for .md files, parses YAML frontmatter, and returns
``{page_content, metadata}`` dicts. List-valued frontmatter (tags, tickers) is flattened
to comma-strings because ChromaDB metadata only accepts str/int/float/bool — a raw list
crashes the add call.
"""

from __future__ import annotations

from pathlib import Path

import frontmatter


def _flatten_value(value):
    """Coerce a frontmatter value into a Chroma-safe scalar, or None to drop it."""
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _skip(path: Path) -> bool:
    # Skip Obsidian's system folder and the blank _TEMPLATE.md placeholders.
    parts = {p.lower() for p in path.parts}
    if ".obsidian" in parts or ".trash" in parts:
        return True
    return path.name.startswith("_")


def load_file(file_path: str) -> dict | None:
    """Parse a single note into a ``{page_content, metadata}`` doc, or None if empty/bad."""
    path = Path(file_path).expanduser()
    if not path.is_file():
        return None
    try:
        post = frontmatter.load(path)
    except Exception:  # noqa: BLE001
        return None
    metadata = {"source": str(path), "filename": path.name}
    for key, raw in post.metadata.items():
        flat = _flatten_value(raw)
        if flat is not None:
            metadata[key] = flat
    body = (post.content or "").strip()
    if not body:
        return None
    return {"page_content": body, "metadata": metadata}


def load_vault(vault_path: str) -> list[dict]:
    """Return a list of ``{page_content, metadata}`` documents for every note."""
    root = Path(vault_path).expanduser()
    if not root.is_dir():
        return []

    docs: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        if _skip(path):
            continue
        doc = load_file(str(path))
        if doc:
            docs.append(doc)
    return docs
