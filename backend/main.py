"""StockBrain FastAPI app entry point.

Pass 1 mounts the search and market routers. Vault/RAG, signals, notes and chat routers
are added in later passes — importing them is guarded so a missing/empty module can never
crash startup.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat as chat_api
from .api import market as market_api
from .api import notes as notes_api
from .api import portfolio as portfolio_api
from .api import search as search_api
from .api import signals as signals_api
from .api import vault as vault_api

app = FastAPI(title="StockBrain", version="2.4.0-slice")

# This backend is localhost-only and uses no cookies, so allow any origin — the Vite dev
# server (localhost:5173) and the packaged Electron app (file://, origin "null") both call it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_api.router)
app.include_router(market_api.router)
app.include_router(signals_api.router)
app.include_router(vault_api.router)
app.include_router(notes_api.router)
app.include_router(chat_api.router)
app.include_router(portfolio_api.router)


@app.on_event("startup")
def _auto_index_vault() -> None:
    """If a vault is configured but the index is empty, build it once on startup.

    Guarded so a missing RAG dependency or bad path can never block the server starting.
    """
    try:
        from . import config
        from .rag import embedder, retriever

        path = config.get_vault_path()
        if path and retriever.is_empty():
            embedder.index_vault(path)
    except Exception:  # noqa: BLE001
        pass


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
