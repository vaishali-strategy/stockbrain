# StockBrain

A local-first, RAG-powered stock market research desktop app focused on Indian
(NSE/BSE) equities. Search any stock for live price, charts, financials, news and an
AI-generated overview — and optionally connect an Obsidian vault to chat over your own
research.

> **Status:** under active construction. Pass 1 (this build) delivers the working
> vertical slice — stock search and a full stock profile page. Signals, vault/RAG chat,
> in-app notes and the packaged Electron app land in later passes. See `PLAN.md` for the
> complete brief.

## Prerequisites
- Python 3.11+ (developed on 3.13)
- Node 18+ (developed on 24)
- Obsidian (optional — the app is fully usable without a vault)

## Quick start
```bash
bash scripts/setup.sh        # venv + deps + fetch Nifty 500 list
cp .env.example .env         # optional: add ANTHROPIC_API_KEY to enable AI overview
npm run dev                  # starts FastAPI backend + Vite frontend
```
No API key is required to search stocks and view price/charts/financials/news.

## Architecture
- `backend/` — FastAPI: `data/` (yfinance + cache + search + overview), `api/` (routes).
- `frontend/` — React + Vite UI.
- `electron/` — desktop wrapper (later pass).
- `obsidian-vault-template/` — starter note templates.

## Building for distribution
Later pass — Electron + PyInstaller sidecar (`npm run build`).

## Contributing
TBD.
