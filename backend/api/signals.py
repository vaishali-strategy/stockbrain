"""AI signals routes.

GET  /signals          — return the cached signals list (with cache age)
POST /signals/refresh  — kick off a fresh screen+score+analyze run (non-blocking)
GET  /signals/status   — live progress of an in-flight run
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from ..signals import analyst

router = APIRouter(tags=["signals"])


@router.get("/signals")
def get_signals() -> dict:
    """Return whatever is cached. The client triggers /signals/refresh to (re)generate."""
    data = analyst.read_cache()
    if not data:
        return {
            "signals": [],
            "generated_at": None,
            "cache_age_minutes": None,
            "total_candidates_scanned": 0,
            "signals_returned": 0,
        }
    return {**data, "cache_age_minutes": analyst.cache_age_minutes()}


@router.post("/signals/refresh")
async def refresh_signals() -> dict:
    """Start a fresh run in the background and return immediately."""
    if analyst.get_progress().get("running"):
        return {"status": "running"}
    # Detach the run so the request returns right away; the client polls /signals/status.
    asyncio.create_task(analyst.run(force=True))
    return {"status": "running"}


@router.get("/signals/status")
def signals_status() -> dict:
    p = analyst.get_progress()
    progress_msg = p.get("message", "Idle")
    if p.get("total"):
        progress_msg = f"{progress_msg} ({p.get('done', 0)}/{p['total']})"
    return {"running": p.get("running", False), "progress": progress_msg}
