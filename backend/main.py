"""StockBrain FastAPI app entry point.

Pass 1 mounts the search and market routers. Vault/RAG, signals, notes and chat routers
are added in later passes — importing them is guarded so a missing/empty module can never
crash startup.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import market as market_api
from .api import search as search_api
from .api import signals as signals_api

app = FastAPI(title="StockBrain", version="2.4.0-slice")

# Allow the Vite dev server and the packaged Electron app to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "app://."],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_api.router)
app.include_router(market_api.router)
app.include_router(signals_api.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
