"""Vault configuration + indexing routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from .. import config
from ..rag import embedder, retriever

router = APIRouter(tags=["vault"])


class VaultConfig(BaseModel):
    path: str


@router.get("/vault-status")
def vault_status() -> dict:
    path = config.get_vault_path()
    configured = bool(path) and Path(path).expanduser().is_dir()
    stats = retriever.stats()
    return {
        "vault_configured": configured,
        "vault_path": path or None,
        "last_synced": config.get_last_synced(),
        "total_notes": stats["total_notes"],
        "total_chunks": stats["total_chunks"],
    }


@router.post("/vault/config")
def set_vault(cfg: VaultConfig) -> dict:
    path = cfg.path.strip()
    if path and not Path(path).expanduser().is_dir():
        return {"ok": False, "error": "That folder does not exist."}
    config.set_vault_path(path)
    return {"ok": True, "vault_path": path or None}


@router.post("/sync-vault")
def sync_vault() -> dict:
    path = config.get_vault_path()
    if not path or not Path(path).expanduser().is_dir():
        return {"error": "No vault configured. Set a vault folder first."}
    result = embedder.index_vault(path)
    config.set_last_synced(datetime.now(timezone.utc).isoformat())
    return result
