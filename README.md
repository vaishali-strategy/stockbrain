# StockBrain

A local-first, RAG-powered stock-market research desktop app focused on Indian (NSE/BSE)
equities. Search any stock for live price, charts, deep fundamentals and technicals, AI
buy/sell signals, and chat over your own Obsidian research — with **no cloud account
required** (a local LLM via Ollama powers the AI, or bring an Anthropic key for the best
quality).

## Features

- **Search → full stock page** — live ₹ quote, price + volume charts (1W → all-time),
  AI/Yahoo company overview, news (Google News, multi-source), financials.
- **Profitability analysis** — a 4-layer read (earnings quality → moat → capital
  allocation → valuation) with a pre-buy checklist, 10-year ROCE/ROE (banks), and a
  plain-English "analyst take" including the moat. Bank-aware.
- **Technical analysis** — RSI, MACD, Stochastic, ADX/DMI, Bollinger Bands, moving
  averages, pivots, Fibonacci, OBV, candlestick patterns, a synthesized rating, and
  suggested buy/target/stop levels.
- **Peer comparison** — sector peers (P/E, ROCE, market cap) from screener.in.
- **AI Signals** — screens the Nifty 100 and produces BUY/SELL/WATCH cards with
  confidence, backed by technicals + fundamentals.
- **Watchlist & Portfolio** — track stocks and holdings (manual or CSV import) with live
  P&L.
- **RAG chat over your Obsidian vault** — ask questions and get answers grounded in your
  own notes + live data, with citations. Works **keyless** via a local Ollama model.

## Prerequisites

- **Python 3.11+** (developed on 3.13)
- **Node 18+** (developed on 24)
- **Obsidian** — optional; the app is fully usable without a vault
- **AI (optional, pick one):**
  - [Ollama](https://ollama.com) for free, offline answers — `ollama run llama3`, or
  - an **Anthropic API key** (pay-as-you-go, [console.anthropic.com](https://console.anthropic.com)) for the best quality

Without either, everything except AI-written text still works (search, charts,
fundamentals, technicals, signals, watchlist, portfolio, and note *retrieval*).

## Quick start

```bash
bash scripts/setup.sh     # venv + deps, fetch ticker lists, seed an example vault, create .env

npm run dev               # browser:  backend + Vite → http://localhost:5173
# or
npm run app               # desktop:  builds the UI and opens the Electron window
```

## Connect your Obsidian vault (optional)

1. Open **Settings → Vault** (gear icon) and point it at your vault folder (a native
   "Browse…" picker appears in the desktop app).
2. Click **Sync vault** to index your notes locally (offline embeddings via `fastembed`).
3. Go to **Chat** and ask, e.g.:
   - *"What's my thesis on HDFC Bank?"*
   - *"Given my notes and today's price, what should I weigh on Reliance?"*
   - *"Summarise my TCS earnings note."*

Indexing and search are 100% local. When you *chat*, the relevant note excerpts + market
data are sent to your chosen LLM (local Ollama stays on your machine; Anthropic is cloud).

## Architecture

```
backend/    FastAPI
  data/     yfinance (market/cache/news/overview), search, fundamentals,
            shareholding + ROCE/peers (screener.in), quality, technicals
  rag/      loader → embedder (fastembed + Chroma) → retriever → chain (Anthropic | Ollama)
  signals/  screener → scorer → analyst (Nifty 100)
  api/      search/stock, market, signals, vault, notes, chat
frontend/   React + Vite (glass/aurora UI)
electron/   desktop wrapper (spawns the backend, native pickers)
scripts/    setup.sh, fetch_nifty100/500.py, seed_vault.py
```

## Configuration (`.env`)

| Key | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` | optional — enables Claude for chat/overview/signals |
| `LLM_PROVIDER` | `auto` (default), `anthropic`, or `ollama` |
| `OLLAMA_MODEL` | local model for keyless chat (default `llama3`) |
| `VAULT_PATH` | Obsidian vault folder (also settable in the UI) |
| `NEWS_API_KEY` | optional — use NewsAPI instead of Google News RSS |

## Building for distribution

`npm run build` is wired for `electron-builder` (dmg / nsis / AppImage). It depends on a
PyInstaller-frozen backend sidecar — **that packaging step is still in progress**; for now
run from source via `setup.sh`.

## Caveats

- Market data is from **yfinance (Yahoo)** — free but **~15 minutes delayed**, not
  real-time ticks.
- Fundamentals from yfinance can be patchy for Indian names; ROCE/ROE, peers and
  shareholding come from **screener.in** (scraped, with breakage detection).
- **Not investment advice.** Signals, levels and analysis are research aids only.

## Contributing

Issues and PRs welcome. See `PLAN.md` for the original build brief.
