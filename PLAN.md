# StockBrain — Claude Code Project Prompt
> Paste this entire file into Claude Code as your first message. It is a complete build brief.

---

## Project identity

You are building **StockBrain** — a local-first, RAG-powered stock market research desktop application. It works in two modes that coexist seamlessly:

1. **Search mode (no setup required)** — Any user can open the app, search any stock ticker, and instantly see live price data, key financials, recent news, and an AI-generated company overview. No Obsidian vault, no notes, no configuration needed. This is the entry point for every user.

2. **Research mode (vault-connected)** — Users who connect their Obsidian vault unlock RAG-powered chat that combines their private notes with live data. The AI cites their own research back to them.

The vault is **entirely optional**. The app must be fully useful without it. A user with zero notes should have a great experience from minute one.

The end goal is a **publishable Electron desktop app** for macOS, Windows, and Linux.

The user is an intermediate developer who is rusty. Write clear code, add concise inline comments on non-obvious lines, and explain your decisions briefly in terminal output as you work. Prefer simplicity over cleverness at every decision point.

---

## Phase 0 — Project scaffold (do this first)

Create the following monorepo structure. Do not skip any file, even if empty.

```
stockbrain/
├── README.md
├── .env.example
├── .gitignore
├── package.json                  # root — Electron + frontend
├── requirements.txt              # Python backend dependencies
│
├── electron/
│   ├── main.js                   # Electron main process
│   └── preload.js                # IPC bridge
│
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── SearchBar.jsx         # NEW: global stock search — primary entry point
│   │   │   ├── StockPage.jsx         # NEW: full stock profile page
│   │   │   ├── StockCard.jsx         # Compact quote widget (price, change, sparkline)
│   │   │   ├── StockChart.jsx        # NEW: full OHLCV price chart (Recharts)
│   │   │   ├── FinancialsTable.jsx   # NEW: revenue, margins, EPS table
│   │   │   ├── NewsFeed.jsx          # NEW: recent news list for a ticker
│   │   │   ├── NoteEditor.jsx        # NEW: create/edit Obsidian note in-app
│   │   │   ├── SignalsDashboard.jsx   # NEW: AI buy/sell signals feed
│   │   │   ├── SignalCard.jsx         # NEW: single signal card component
│   │   │   ├── ChatPanel.jsx         # AI chat (works without vault)
│   │   │   ├── Watchlist.jsx
│   │   │   ├── ObsidianSync.jsx
│   │   │   └── Sidebar.jsx
│   │   └── styles/
│   │       └── globals.css
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── embedder.py
│   │   ├── retriever.py
│   │   └── chain.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── market.py             # yfinance: quote, history, financials
│   │   ├── news.py               # news fetcher
│   │   ├── search.py             # NEW: ticker search / company lookup
│   │   ├── overview.py           # NEW: AI-generated company overview
│   │   └── cache.py              # NEW: on-disk daily OHLCV cache (yfinance reliability)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── vault.py
│   │   ├── market.py             # quote, chart, financials, news
│   │   ├── search.py             # NEW: GET /search?q=apple
│   │   ├── notes.py              # NEW: POST /notes (save note to vault)
│   │   └── signals.py            # NEW: GET /signals, POST /signals/refresh
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── screener.py           # Scans Nifty 500 for candidates
│   │   ├── scorer.py             # Technical + fundamental scoring
│   │   └── analyst.py            # Claude generates final signal card per stock
│   ├── tests/
│   │   └── test_scorer.py        # NEW: unit tests for RSI + signal/confidence logic
│   └── db/
│       └── chroma/
│
├── obsidian-vault-template/
│   ├── Companies/_TEMPLATE.md
│   ├── Sectors/_TEMPLATE.md
│   ├── Earnings/_TEMPLATE.md
│   ├── Thesis/_TEMPLATE.md
│   ├── News/_TEMPLATE.md
│   ├── Concepts/_TEMPLATE.md
│   ├── Watchlist/Active.md
│   └── Journal/_TEMPLATE.md
│
└── scripts/
    ├── setup.sh
    └── seed_vault.py
```

After scaffolding, run `git init` and make an initial commit.

---

## Phase 1 — Obsidian vault template

Populate every `_TEMPLATE.md` with production-ready YAML frontmatter and section headers. The templates must be immediately usable — not placeholder text.

### Companies/_TEMPLATE.md
```markdown
---
ticker: TICKER
company: Full Company Name
sector: Sector
type: company
market_cap: large | mid | small
exchange: NYSE | NASDAQ | NSE | BSE
tags: []
sentiment: bullish | bearish | neutral
position: long | short | none
confidence: high | medium | low
last_updated: YYYY-MM-DD
---

## Business summary


## Why I'm watching this


## Key metrics
- Revenue growth YoY: 
- Gross margin: 
- Net margin: 
- P/E ratio: 
- Debt/equity: 
- Free cash flow: 

## Moat analysis


## Bull case


## Bear case


## Key risks


## Linked notes
- 

## My observations

```

### Earnings/_TEMPLATE.md
```markdown
---
ticker: TICKER
quarter: Q1 | Q2 | Q3 | Q4
year: YYYY
type: earnings
beat_miss: beat | miss | in-line
tags: []
date: YYYY-MM-DD
---

## Headline numbers
- Revenue: X vs estimate Y
- EPS: X vs estimate Y
- Guidance next quarter: 

## Management commentary (key quotes)


## What surprised me


## How this changes my thesis


## Linked company note
- [[TICKER]]
```

### Thesis/_TEMPLATE.md
```markdown
---
ticker: TICKER
direction: bull | bear
type: thesis
conviction: high | medium | low
time_horizon: short | medium | long
entry_target: 
exit_target: 
stop_loss: 
tags: []
created: YYYY-MM-DD
---

## Core thesis (one paragraph)


## Catalysts I'm watching
1. 
2. 
3. 

## What would invalidate this thesis


## Position sizing rationale


## Linked notes
- [[TICKER]]
```

### News/_TEMPLATE.md
```markdown
---
tickers: []
type: news
source: 
url: 
date: YYYY-MM-DD
tags: []
sentiment_impact: positive | negative | neutral
---

## Summary (in my own words)


## Why this matters


## My reaction

```

### Journal/_TEMPLATE.md
```markdown
---
date: YYYY-MM-DD
type: journal
tags: []
---

## Market mood today


## Decisions I made


## Trades executed
| Ticker | Action | Price | Qty | Reason |
|--------|--------|-------|-----|--------|
|        |        |       |     |        |

## What I learned


## Tomorrow's focus

```

Also create `obsidian-vault-template/Watchlist/Active.md`:
```markdown
---
type: watchlist
last_updated: YYYY-MM-DD
---

## Active watchlist

| Ticker | Sector | Sentiment | Entry target | Notes |
|--------|--------|-----------|--------------|-------|
|        |        |           |              |       |

## On deck (researching)

## Graduated to position

## Removed from watchlist
```

Then run `scripts/seed_vault.py` to generate 3 realistic example notes using **Indian stocks**:
- `Companies/RELIANCE.md` — Reliance Industries example (NSE: RELIANCE)
- `Earnings/TCS_Q3_2025.md` — TCS Q3 FY2025 earnings note
- `Thesis/Bull_HDFCBANK.md` — Bull thesis for HDFC Bank

Use realistic but clearly educational content. Prices in ₹. Reference Indian market context (Nifty, Sensex, RBI policy, FII/DII flows).

---

## Phase 2 — Python backend

### Setup
Install all dependencies into a virtual environment:
```
anthropic
langchain
langchain-anthropic
langchain-chroma
chromadb
fastembed          # local ONNX embeddings — free, offline, no torch (do NOT add openai/torch)
fastapi
uvicorn
python-dotenv
yfinance
requests
python-frontmatter
watchdog
pytest             # unit tests for scorer logic
```

Write these to `requirements.txt`.

### config.py
Load from `.env`:
```python
ANTHROPIC_API_KEY=
VAULT_PATH=          # absolute path to user's Obsidian vault
CHROMA_PATH=./backend/db/chroma
NEWS_API_KEY=        # optional, for NewsAPI.org
EMBED_MODEL=BAAI/bge-small-en-v1.5        # local ONNX via fastembed — free, offline, no torch
SIGNALS_MODEL=claude-haiku-4-5-20251001   # high-volume signal cards (cheap)
CHAT_MODEL=claude-sonnet-4-6              # RAG chat
OVERVIEW_MODEL=claude-sonnet-4-6          # company overviews
# AGENT_MODEL=claude-opus-4-8             # reserved for a future agentic research engine
```

### backend/rag/loader.py
- Walk the vault directory recursively for all `.md` files
- Parse YAML frontmatter using `python-frontmatter`
- Return a list of `Document` objects (LangChain format) with:
  - `page_content`: the markdown body
  - `metadata`: all frontmatter fields + `source` (file path) + `filename`
- **Flatten list-valued frontmatter (e.g. `tags: []`, `tickers: []`) to comma-joined strings before putting them in metadata.** ChromaDB metadata accepts only str/int/float/bool — list values crash the embed call.
- Skip files in `.obsidian/` system folder
- Log how many files were loaded

### backend/rag/embedder.py
- Chunk documents using `RecursiveCharacterTextSplitter` with `chunk_size=800`, `overlap=100`
- Embed using **local ONNX embeddings via `fastembed`** (model `EMBED_MODEL`, default `BAAI/bge-small-en-v1.5`). Wrap it in a LangChain-compatible `Embeddings` interface (or use `langchain-community`'s `FastEmbedEmbeddings`). **Do NOT use `OpenAIEmbeddings` — there is no OpenAI key, and Anthropic has no embeddings API.** No torch dependency.
- Persist to ChromaDB at `CHROMA_PATH`
- Support incremental updates: only re-embed files that changed since last sync (compare file mtime)
- **On incremental update, delete the file's existing chunks before re-adding** (`collection.delete(where={"source": file_path})`, then add). Re-adding without deleting leaves stale duplicate chunks in Chroma.
- Expose `embed_single_file(file_path)` to index one note immediately after it is saved (used by `api/notes.py`)
- Print progress: "Embedding 47 chunks from 12 files..."

### backend/rag/retriever.py
- Load the persisted ChromaDB collection
- Expose a `retrieve(query, filters=None, k=6)` function
- `filters` maps to ChromaDB metadata filtering — e.g. `{"ticker": "NVDA"}` or `{"type": "earnings"}`
- Return retrieved docs with their metadata intact

### backend/rag/chain.py
Build a LangChain RAG chain (using `CHAT_MODEL`, default `claude-sonnet-4-6`; **enable prompt caching on the system prompt**) that:
1. Takes a user query + optional ticker context
2. Retrieves relevant vault chunks
3. Fetches live price + recent news for mentioned tickers (call `data/market.py`)
4. Constructs this system prompt:

```
You are StockBrain, an expert stock market research assistant.

You have access to the user's private Obsidian research vault — their personal notes, investment theses, earnings observations, and watchlists. Treat this as ground truth for their views and research.

You also have access to live market data and recent news.

When answering:
- Always cite which note or source you're drawing from (e.g. "From your NVDA thesis note...")
- Distinguish clearly between the user's own research and external data
- Be direct about uncertainty — if the vault doesn't have information on something, say so
- Never fabricate financial data. If you don't have a number, say you don't have it.
- Format responses with clear headers when answering multi-part questions

Vault context:
{vault_context}

Live market data:
{market_context}

User question: {question}
```

5. Stream the response token-by-token
6. Return source documents used in the answer

### backend/data/market.py
Using `yfinance`:
- `get_quote(ticker)` → current price, % change, volume, market cap, P/E
- `get_history(ticker, period="3mo")` → OHLCV dataframe
- `get_financials(ticker)` → revenue, margins, EPS (last 4 quarters)
- Handle errors gracefully — if yfinance fails, return `{"error": "Could not fetch data for TICKER"}`
- **Add retry-with-backoff** around every yfinance call — `.NS`/`.BO` tickers rate-limit frequently. Read daily history through `data/cache.py` rather than hitting yfinance on every call.

### backend/data/cache.py (NEW — yfinance reliability layer)
yfinance on NSE/BSE is rate-limit-prone, and the signals screener needs ~500 tickers per run. A naive per-ticker fetch will be slow and get throttled.
- On-disk daily-OHLCV cache (SQLite or parquet) keyed by `ticker + date`. Callers read from cache; only stale/missing tickers are refetched.
- Bulk-fetch history via `yf.download([...tickers...], group_by="ticker")` — never loop one ticker at a time for the screener.
- Retry-with-backoff + per-ticker failure skip so one bad ticker never breaks a run.

### backend/data/search.py (NEW)
- `search_ticker(query: str)` — takes a freeform string like "Reliance", "TCS", "Nifty IT"
- **Indian stocks are the primary target.** All search logic prioritizes NSE/BSE results.
- Strategy (the bundled JSON is the PRIMARY path — `yfinance.search()` is unreliable for Indian names):
  1. Fuzzy-match `query` against the bundled `nifty500_tickers.json` (name → ticker map) — e.g. "tata motors" → `TATAMOTORS.NS`. Fast, offline, and the main matcher.
  2. If the query already looks like a ticker, try `{query}.NS` (NSE) directly via yfinance, then `{query}.BO` (BSE) as fallback.
  3. Only as a last resort, use `yfinance.search()` and filter results to `.NS` / `.BO` suffixed tickers.
- Returns a list of `{ ticker, name, exchange, sector, market_cap_category }` dicts, max 10 results
- Exchange badge: show "NSE" or "BSE" prominently — never show raw `.NS`/`.BO` suffix to the user
- Include a `nifty500_tickers.json` file in `backend/data/` with the full Nifty 500 ticker list (download from NSE open data and bundle it — do not fetch at runtime)

### backend/data/overview.py (NEW)
- `get_company_overview(ticker: str)` — generates a structured company profile
- Fetches from yfinance: `info` dict (longBusinessSummary, sector, industry, employees, website, country)
- Calls Claude API (`OVERVIEW_MODEL`, default `claude-sonnet-4-6`) to produce a clean 3-paragraph summary: what the company does, its competitive position, and key things an investor should know
- Returns: `{ summary, sector, industry, employees, website, country, founded, description_raw }`
- Cache the AI summary in a local JSON file at `backend/db/overviews/{ticker}.json` — regenerate only if older than 7 days

### backend/data/news.py
- `get_news(ticker, limit=5)` — fetch from NewsAPI if key present, otherwise use yfinance's built-in news
- Return list of `{title, url, source, published_at, summary}` dicts

### backend/api/chat.py
`POST /chat`
```json
Request:  { "message": "string", "ticker_context": "NVDA", "conversation_history": [] }
Response: streaming SSE — each chunk is { "token": "...", "done": false }
Final:    { "token": "", "done": true, "sources": [...] }
```

The chat endpoint must handle the **vault-less state gracefully**:
- If no vault is configured or ChromaDB is empty, skip RAG retrieval entirely
- Still answer using live market data + Claude's knowledge
- Include a subtle note in the response: "💡 Connect your Obsidian vault to include your personal research in answers."

### backend/api/search.py (NEW)
- `GET /search?q=apple` — calls `data/search.py`, returns ticker list
- `GET /stock/{ticker}` — returns a full stock profile in one call:
  ```json
  {
    "quote": { price, change_pct, volume, market_cap, pe_ratio, 52w_high, 52w_low },
    "overview": { summary, sector, industry, employees, website },
    "financials": { revenue_ttm, gross_margin, net_margin, eps_ttm, debt_equity },
    "news": [ ...5 items... ],
    "chart": { period: "3mo", ohlcv: [...] },
    "has_vault_notes": true | false,
    "vault_note_count": N
  }
  ```
- This single endpoint powers the entire StockPage view — one call, everything needed

### backend/api/notes.py (NEW)
- `POST /notes` — saves a note to the vault
  ```json
  Request: {
    "ticker": "NVDA",
    "note_type": "company | earnings | thesis | news | journal",
    "content": "markdown string",
    "frontmatter": { ...key-value pairs... }
  }
  ```
  - Assembles the complete `.md` file with YAML frontmatter
  - Saves to the correct subfolder in the vault (e.g. `Companies/NVDA.md`)
  - If file already exists, creates `NVDA_2.md` — never overwrites without asking
  - Triggers an incremental vault re-index for just this file
  - Returns `{ "path": "absolute/path/to/file", "indexed": true }`
- `GET /notes/{ticker}` — returns all vault notes for a ticker as a list

### backend/api/vault.py
- `POST /sync-vault` — triggers full re-index of the vault. Returns `{ "files_indexed": N, "chunks_created": M }`
- `GET /vault-status` — returns `{ "last_synced": "ISO timestamp", "total_notes": N, "total_chunks": M, "vault_configured": true|false }`
- `POST /watch-vault` — starts a `watchdog` file watcher that auto-re-embeds changed files

### backend/api/market.py
- `GET /quote/{ticker}` — returns live quote
- `GET /news/{ticker}` — returns recent news
- `GET /chart/{ticker}?period=3mo` — returns OHLCV JSON for charting

### backend/main.py
- FastAPI app
- Mount all routers
- CORS enabled for `localhost:5173` (Vite dev) and `app://` (Electron)
- On startup: check ChromaDB has data; if not, auto-trigger vault sync
- Health endpoint: `GET /health`

---

## Phase 2.5 — AI signals engine

This is the core new feature. The app analyzes the Nifty 500 universe and produces a curated list of buy/sell/watch signals backed by data and explained in plain language. No autonomous trading. No order placement. Pure analysis and suggestion.

### How it works (end to end)

1. `screener.py` scans the Nifty 500 list and filters down to **candidates** — stocks worth analyzing further — based on fast, cheap data checks
2. `scorer.py` pulls full data for each candidate and computes a structured score object
3. `analyst.py` sends each scored candidate to Claude, which produces a human-readable signal card
4. Results are cached for 4 hours so the user isn't waiting for a fresh Claude call every time they open the signals tab

### backend/signals/screener.py

Scans `nifty500_tickers.json` and returns a shortlist of 15-25 candidates per run. **Read all price history through `data/cache.py` and fetch in bulk via `yf.download(...)`** — per-ticker sequential calls over 500 names will rate-limit and time out.

Filter criteria (stocks must pass ALL of these to become a candidate):
- Average daily volume > 500,000 shares (liquid enough to trade)
- 52-week high/low range available (data quality check)
- Not in the "suspended/delisted" state on NSE

Then rank by these signals and take the top 20:
- RSI < 35 → oversold → potential buy candidate
- RSI > 68 → overbought → potential sell candidate
- Price crossed above 50-day MA in last 3 trading days → momentum
- Price crossed below 50-day MA in last 3 trading days → breakdown
- Volume spike: today's volume > 2x 20-day average volume

Use `yfinance` for all data. Compute RSI using a simple 14-period Wilder method (write it manually — do not add ta-lib as a dependency). Compute moving averages as a rolling mean of closing prices.

```python
def compute_rsi(prices: list[float], period: int = 14) -> float:
    # Returns the most recent RSI value (0-100)
    # Use Wilder smoothing (exponential, alpha = 1/period)
```

### backend/signals/scorer.py

For each candidate ticker, produce a structured `SignalScore` datadict:

```python
{
  "ticker": "RELIANCE.NS",
  "display_name": "Reliance Industries",
  "sector": "Energy",
  "signal_type": "BUY" | "SELL" | "WATCH",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "current_price": 2840.50,
  "change_pct_today": 1.23,
  "rsi": 31.4,
  "vs_50dma": -3.2,       # % above/below 50-day MA (negative = below)
  "vs_200dma": 8.7,       # % above/below 200-day MA
  "volume_ratio": 2.4,    # today's volume / 20-day avg volume
  "pe_ratio": 24.1,
  "week52_high": 3217.00,
  "week52_low": 2180.00,
  "pct_from_52w_high": -11.7,
  "revenue_growth_yoy": 8.4,   # from yfinance financials, can be None
  "net_margin": 9.2,           # can be None
  "technicals_summary": "Oversold on RSI, volume surge, near 52-week support",
  "fundamentals_summary": "Healthy margins, moderate growth",
  "vault_has_notes": false,    # check ChromaDB for this ticker
  "scored_at": "2026-05-31T09:30:00+05:30"
}
```

Signal type logic:
- `BUY` if: RSI < 38 AND (vs_50dma > -8%) AND pe_ratio < 40 (or pe unavailable)
- `SELL` if: RSI > 65 AND vs_50dma > 5% AND pct_from_52w_high > -5%
- `WATCH` for everything else that passed the screener

Confidence logic:
- `HIGH` if 3+ indicators agree (e.g. RSI oversold + volume spike + near 52w support)
- `MEDIUM` if 2 indicators agree
- `LOW` if only 1 indicator

### backend/signals/analyst.py

Calls Claude API (`SIGNALS_MODEL`, default `claude-haiku-4-5-20251001` — cheap, high-volume) once per candidate to generate a signal card explanation. **Enable prompt caching on the system prompt** (identical across all ~20 candidates) via a `cache_control` breakpoint.

System prompt:
```
You are StockBrain's stock analyst. You analyze Indian stocks listed on NSE/BSE.

Your job: given structured data about a stock, write a concise, honest signal card that helps a retail investor decide whether to investigate further.

Rules:
- Write in plain English. No jargon unless explained.
- Be direct. If the signal is weak, say so.
- Never guarantee returns. Never say "will go up" or "guaranteed". Use "suggests", "indicates", "may".
- Always mention at least one risk, even for strong BUY signals.
- Keep the entire output under 120 words.
- Output only the analysis text — no headers, no bullet points, no markdown.
```

User prompt template:
```
Stock: {display_name} ({ticker}) — {sector}
Signal: {signal_type} | Confidence: {confidence}
Price: ₹{current_price} | Change today: {change_pct_today}%
RSI (14): {rsi} | vs 50-DMA: {vs_50dma}% | vs 200-DMA: {vs_200dma}%
Volume ratio: {volume_ratio}x average
P/E: {pe_ratio} | Net margin: {net_margin}% | Revenue growth YoY: {revenue_growth_yoy}%
52-week range: ₹{week52_low} – ₹{week52_high} (currently {pct_from_52w_high}% from high)
Technicals: {technicals_summary}
Fundamentals: {fundamentals_summary}
{vault_context_line}

Write a concise signal analysis (under 120 words).
```

Where `vault_context_line` is either:
- `"User has personal research notes on this stock."` — if `vault_has_notes` is true
- `""` — if no notes

Cache the result: store `{ ticker, signal_card_text, scored_at, signal_type, confidence }` in `backend/db/signals_cache.json`. Regenerate only if cache entry is older than 4 hours.

Process all candidates in parallel using `asyncio.gather` — do not call Claude sequentially. **Guard all writes to `signals_cache.json` and the module-level progress dict with an `asyncio.Lock`** — parallel tasks writing the same JSON will corrupt it. Add a per-run ceiling on Claude calls so a refresh can never blow the API budget.

### backend/api/signals.py

- `GET /signals` — returns the full signals list from cache (or triggers a fresh run if cache is stale/empty)
  ```json
  {
    "signals": [ ...SignalScore + { "analysis": "..." } ... ],
    "generated_at": "ISO timestamp",
    "cache_age_minutes": 47,
    "total_candidates_scanned": 500,
    "signals_returned": 18
  }
  ```
- `POST /signals/refresh` — forces a fresh screen + score + analyze run. Returns immediately with `{ "status": "running" }`. Client polls `GET /signals` until `cache_age_minutes` resets.
- `GET /signals/status` — returns `{ "running": true|false, "progress": "Scoring 12/20 candidates..." }`

Progress updates: use a module-level `dict` to track run state. The analyst updates it as it processes each ticker.

---

## Phase 3 — Frontend (React + Vite)

Use Vite + React. No UI framework — use plain CSS with CSS variables for theming. The app should feel like a Bloomberg Terminal meets Notion — premium, data-dense, dark-mode by default.

### App states / routing (no React Router needed — use simple state machine)
```
STATES:
  home       → SearchBar centered, recent searches, top movers
  stock      → Full StockPage for a searched ticker
  chat       → Chat panel (with optional ticker context)
  settings   → Vault config, API keys
```

### Layout (stock state)
```
┌─────────────┬──────────────────────────────────────────┐
│  Sidebar    │  StockPage                               │
│             │  ┌─────────┬──────────────┬───────────┐ │
│  SearchBar  │  │ Quote   │ Overview     │ Notes     │ │
│  Watchlist  │  │ card    │ (AI summary) │ panel     │ │
│  Recent     │  ├─────────┴──────────────┤           │ │
│  searches   │  │ Price chart (3mo)      │ [+] Add   │ │
│             │  ├────────────────────────┤ note btn  │ │
│             │  │ Financials table       │           │ │
│             │  ├────────────────────────┤           │ │
│             │  │ News feed              │           │ │
│             │  └────────────────────────┴───────────┘ │
└─────────────┴──────────────────────────────────────────┘
```

### SearchBar.jsx (NEW — primary entry point)
- Large centered search input on home screen
- As user types, hits `GET /search?q=...` with 300ms debounce
- Shows dropdown of matching tickers with name + exchange + sector
- Also accepts direct ticker entry (type "NVDA" → Enter)
- Supports Indian stocks: show NSE/BSE badge on Indian results
- Recent searches stored in localStorage, shown below input on focus
- On selection → transition to stock state, load StockPage

### StockPage.jsx (NEW — core feature)
Calls `GET /stock/{ticker}` on mount. Shows a loading skeleton while fetching. Then renders:

**Header row:** Ticker, company name, exchange badge, `[+ Add to watchlist]` button, `[Open in chat]` button

**Quote card (StockCard.jsx):**
- Price (large, prominent)
- % change today (green if positive, red if negative)
- Volume, market cap, P/E, 52-week range
- Auto-refreshes every 60 seconds

**StockChart.jsx (NEW):**
- Uses `recharts` LineChart plotting the **closing price** (recharts has no native candlestick — line-of-closes only; don't promise OHLC candles)
- Period toggle: 1W / 1M / 3M / 6M / 1Y
- Tooltips showing OHLCV values for the hovered point
- Line color matches the period's direction (green/red)

**Overview section:**
- AI-generated 3-paragraph company summary (from `/stock/{ticker}` → `overview.summary`)
- Sector, industry, employees, website as chips below

**FinancialsTable.jsx (NEW):**
- Clean table: Revenue TTM, Gross Margin, Net Margin, EPS, Debt/Equity
- Color-code positive/negative margins
- "Data via Yahoo Finance" attribution link

**NewsFeed.jsx (NEW):**
- List of 5 recent headlines
- Each: headline, source, time ago, external link icon
- Clicking opens in system browser (via `window.electronAPI.openExternal`)

**Notes panel (right column):**
- If vault is configured and has notes for this ticker: show them as cards (filename, first 100 chars, date)
- If no notes exist: show empty state with `[Write a note about {ticker}]` button
- If vault not configured: show `[Connect Obsidian vault to save notes]` prompt

### SignalsDashboard.jsx (NEW — primary feature surface)

A dedicated tab/view accessible from the sidebar. This is where the AI buy/sell signals live.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  AI Signals                    [🔄 Refresh]  [Last updated: X min ago] │
│                                                             │
│  Filters: [All ▾]  [BUY]  [SELL]  [WATCH]  [High confidence only]    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ SignalCard   │  │ SignalCard   │  │ SignalCard   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

On mount: `GET /signals`. If signals are fresh (cache_age_minutes < 240), show them immediately. If stale, show last results with a "Refresh for latest" banner.

`[Refresh]` button: calls `POST /signals/refresh`, then polls `GET /signals/status` every 2 seconds to show a progress message ("Scanning Nifty 500... Scoring 12/20 stocks... Generating analysis..."). When done, re-fetches `GET /signals` and re-renders.

Filter bar: client-side filtering only — no re-fetch. Filters by signal_type and confidence.

Empty state: if no signals yet and not running, show "Click Refresh to generate your first signals" with a large refresh button.

Disclaimer footer (always visible, subtle):
> "StockBrain signals are for research purposes only. Not financial advice. Always do your own due diligence before investing."

### SignalCard.jsx (NEW)

Displays one signal. Compact card, ~280px wide, suitable for a responsive grid.

**Card anatomy:**
```
┌────────────────────────────────────┐
│  RELIANCE ● NSE              [BUY] │  ← ticker + exchange + signal badge
│  Reliance Industries               │  ← full name
│  ₹2,840  +1.2% today   ● HIGH     │  ← price + change + confidence dot
├────────────────────────────────────┤
│  RSI 31 · Vol 2.4x · -3% vs 50DMA │  ← key technicals in one line
├────────────────────────────────────┤
│  "Oversold on RSI with a volume    │
│  surge suggests short-term buying  │
│  interest. Strong fundamentals     │  ← Claude's analysis text
│  support the thesis, though broad  │
│  market weakness remains a risk."  │
├────────────────────────────────────┤
│  [View stock]        [Write a note]│  ← actions
└────────────────────────────────────┘
```

Signal badge colors:
- BUY → green background, white text
- SELL → red background, white text
- WATCH → amber background, dark text

Confidence dot:
- HIGH → solid green dot
- MEDIUM → solid amber dot
- LOW → solid gray dot

`[View stock]` → navigates to StockPage for that ticker
`[Write a note]` → opens NoteEditor pre-filled with ticker + signal context

If `vault_has_notes` is true on the signal, show a small 📓 icon on the card — the user has prior research on this one.

### NoteEditor.jsx (NEW)
- Opens as a slide-in panel (not a modal — keep the stock data visible)
- Dropdown: select note type (Company / Earnings / Thesis / News / Journal)
- Pre-fills YAML frontmatter automatically from the stock data already loaded (ticker, sector, date)
- Markdown textarea with basic toolbar: Bold, Italic, Headers, bullet list
- Live preview toggle
- `[Save to vault]` button → calls `POST /notes` → shows success toast → triggers vault re-index
- If vault not configured: `[Save to vault]` button instead opens vault setup flow

### ChatPanel.jsx
- Streaming message rendering
- User messages on right, StockBrain on left
- When vault is empty/unconfigured: show a soft banner at top:
  > "You're in data mode — answers use live market data and AI knowledge. Connect your Obsidian vault to include your personal research."
- Show "Sources used" as collapsible chips under each AI response
- `Cmd+K` focuses input

### Watchlist.jsx
- Shows tickers from vault `Watchlist/Active.md` if vault connected
- If no vault: shows manually added tickers (stored in localStorage)
- `[+ Add]` button adds current stock to watchlist
- Click a ticker → loads StockPage for that ticker

### ObsidianSync.jsx
- First-run: prompt to select vault folder (calls `window.electronAPI.selectVaultFolder()`)
- Shows vault status: last sync time, note count, chunk count
- `[Sync vault]` button with progress indicator
- `[Open vault in Obsidian]` button

### Sidebar.jsx
- App name: **StockBrain**
- SearchBar (compact version — just an icon + click to focus home search)
- **AI Signals** nav link (with a badge showing count of HIGH confidence signals)
- Watchlist section
- Recent stocks viewed (last 5)
- Settings icon → settings state

---

## Phase 4 — Electron wrapper

### electron/main.js
- Open a `BrowserWindow` loading the Vite frontend
- On app ready: spawn the Python FastAPI backend as a child process
- Handle backend startup — wait for `/health` to return 200 before showing window (show a loading screen)
- On app quit: kill the Python process cleanly
- Set a sensible window size: 1280×800, min 960×600

### electron/preload.js
- Expose `window.electronAPI` with:
  - `selectVaultFolder()` → opens OS folder picker, returns path
  - `getAppVersion()` → from package.json
  - `openExternal(url)` → opens links in system browser

### package.json
Configure:
- `electron-builder` for packaging
- Build targets: macOS (dmg), Windows (nsis), Linux (AppImage)
- App name: StockBrain
- Python backend bundled as a sidecar binary (use PyInstaller to freeze it)

---

## Phase 5 — Developer scripts

### scripts/setup.sh
```bash
#!/bin/bash
echo "Setting up StockBrain..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
cp .env.example .env
echo "Fetching Nifty 500 ticker list..."
python scripts/fetch_nifty500.py
echo "Seeding example vault notes..."
python scripts/seed_vault.py
echo "Done. Edit .env with your Anthropic API key, then run: npm run dev"
```

### scripts/fetch_nifty500.py (NEW)
- Downloads the Nifty 500 constituents CSV from NSE's public URL: `https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv`
- Parses it into a dict of `{ "Company Name": "TICKER.NS" }`
- Also stores `{ ticker, name, sector, series }` as a list for search
- Saves to `backend/data/nifty500_tickers.json`
- If the download fails (network issue), falls back to a hardcoded list of the top 50 Nifty stocks bundled in the script itself — so setup never fails

### scripts/seed_vault.py
Generate the three Indian stock example notes with realistic content.

### package.json scripts
```json
"scripts": {
  "dev:frontend": "vite frontend/",
  "dev:backend": "uvicorn backend.main:app --reload --port 8000",
  "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
  "electron": "electron .",
  "build:backend": "pyinstaller backend/main.py --onefile --name stockbrain-server",
  "build": "npm run build:backend && electron-builder",
  "seed": "python scripts/seed_vault.py"
}
```

---

## Phase 6 — README.md

Write a proper README covering:
1. What StockBrain is (2 sentences)
2. Prerequisites: Python 3.11+, Node 18+, Obsidian (optional but recommended)
3. Quick start (copy the setup.sh commands)
4. How to point it at your Obsidian vault
5. Example questions you can ask it
6. Architecture overview (reference the folder structure)
7. How to build for distribution
8. Contributing section (placeholder)

---

## Build order — execute in this exact sequence

1. Scaffold the full directory structure
2. Create all Obsidian template files (Phase 1)
3. Run `seed_vault.py` to generate example notes
4. Build the Python backend (Phase 2):
   - Start with `data/search.py` + `data/market.py` — these are the foundation
   - Build `api/search.py` → test `GET /search?q=apple` and `GET /stock/NVDA`
   - Build `data/overview.py` → test AI summary generation
   - Build `api/notes.py` → test note saving
   - Build RAG modules last — they're optional for basic functionality
   - Build `api/chat.py` → test streaming with and without vault
4.5. Build the signals engine (Phase 2.5):
   - Build `signals/screener.py` → test with `python -m backend.signals.screener` — should return 15-25 tickers
   - Build `signals/scorer.py` → test scoring on 3 tickers manually
   - Build `signals/analyst.py` → test one Claude call, inspect the output
   - Build `api/signals.py` → test `GET /signals` end-to-end
5. Verify with curl before touching frontend:
   - `curl "localhost:8000/search?q=nvidia"` → returns ticker list
   - `curl "localhost:8000/stock/NVDA"` → returns full profile JSON
6. Build the React frontend (Phase 3):
   - Start with SearchBar + StockPage — this is the core UX
   - Add NoteEditor next
   - Add ChatPanel last
7. Wire Electron (Phase 4)
8. End-to-end test: open Signals tab → refresh → see signal cards → click "View stock" on a BUY signal → see stock page → write a note → open chat → ask about the stock
9. Write README

---

## Quality gates — do not move to the next phase until these pass

**After Phase 2 (backend):**
- `curl "localhost:8000/search?q=apple"` returns ≥3 results with tickers
- `curl "localhost:8000/stock/NVDA"` returns quote + overview + financials + news in one response
- `curl -X POST localhost:8000/notes -H "Content-Type: application/json" -d '{"ticker":"NVDA","note_type":"company","content":"Test note","frontmatter":{}}'` creates a file
- `curl -X POST localhost:8000/chat -d '{"message":"tell me about Apple stock"}'` streams a response **even with no vault configured**

**After Phase 2 (embeddings/RAG):**
- Indexing the vault runs fully offline with no OpenAI/torch import; Chroma persists with list frontmatter flattened to comma-strings (no metadata crash)
- Re-indexing the same file twice does NOT grow the chunk count (delete-before-add works)
- `pytest backend/tests/test_scorer.py` passes (RSI + signal/confidence logic)

**After Phase 2.5 (signals engine):**
- `python -m backend.signals.screener` returns 15-25 Nifty tickers in < 60 seconds **on a warm cache** (first cold run may take several minutes while the OHLCV cache fills)
- `curl localhost:8000/signals` returns at least 5 signal cards with non-empty `analysis` text
- `curl -X POST localhost:8000/signals/refresh` returns `{"status": "running"}` immediately (non-blocking)
- Each signal card has `signal_type`, `confidence`, `current_price` in ₹, and `analysis` under 120 words

**After Phase 3 (frontend):**
- Typing "Reliance" in search shows a dropdown with RELIANCE.NS
- Clicking AAPL loads the full stock page with real price data
- `[Write a note]` button opens NoteEditor, saving creates an `.md` file
- Chat works and shows the vault-less banner when no vault is connected

**After Phase 4 (Electron):**
- App launches to the home search screen without a terminal
- Backend starts and stops cleanly with the app
- Vault folder picker works on the OS
- External news links open in the system browser

---

## Constraints and non-negotiables

- No hardcoded API keys anywhere — always from `.env`
- `.env` and `backend/db/chroma/` must be in `.gitignore`
- All financial data fetching must have error handling with user-facing fallback messages
- **The app must be fully useful with zero Obsidian setup.** Stock search, stock page, news, financials, and AI chat must all work with no vault configured. Never block the user on vault setup.
- The vault is an enhancement, not a requirement — always show a graceful empty state, never an error, when no vault is present
- AI-generated company overviews must be cached locally — do not call Claude API on every page load
- Do not use any paid data APIs in the default setup — yfinance is free and sufficient for v1
- **Indian stocks (NSE/BSE) are the primary and default market.** Every data fetch uses `.NS` suffix first, `.BO` as fallback. US stocks are not in scope for v1 — do not spend time on them.
- All currency displays default to ₹ (INR). Never show $ unless the data explicitly comes in USD.
- Price data is in INR from yfinance for `.NS`/`.BO` tickers — display as-is, no conversion needed.
- Market hours context: NSE trading hours are 9:15 AM – 3:30 PM IST. Show "Market open" / "Market closed" status accordingly. The user's timezone is IST.
- The bundled `nifty500_tickers.json` must be present before the app runs — include a `scripts/fetch_nifty500.py` that downloads and saves it from NSE's public data (run once during setup).
- **Embeddings are local-only via `fastembed` (ONNX). Never add `openai` or `torch`.** Anthropic has no embeddings API; do not attempt `AnthropicEmbeddings`.
- **Model IDs come from config, never hardcoded:** `SIGNALS_MODEL` = Haiku 4.5 (`claude-haiku-4-5-20251001`), `CHAT_MODEL`/`OVERVIEW_MODEL` = Sonnet 4.6 (`claude-sonnet-4-6`). Opus 4.8 (`claude-opus-4-8`) is reserved for a future agentic-research engine. Do not use retired snapshot IDs like `claude-sonnet-4-20250514`.
- **Enable Anthropic prompt caching** on repeated system prompts (signal analyst, chat) and cap Claude calls per run so a refresh cannot blow the API budget.
- **No SEC EDGAR / US filings.** SEC EDGAR has no NSE/BSE data — filings are out of scope for v1; rely on news + financials.
- **Compliance framing (SEBI):** signals are research/educational, not investment advice. Keep the disclaimer visible on every signals surface; use "suggests/indicates/may", never guarantees.
- **Privacy disclosure:** chat sends vault note content and market data to Anthropic. Disclose this once in onboarding/settings — a real caveat to the "local-first" framing.
- `recharts` is the only charting library — do not add others
- Python code uses type hints throughout
- React components use functional components + hooks only (no class components)
- Store user preferences (recent searches, manual watchlist, vault path) in Electron's `app.getPath('userData')` — not hardcoded paths

---

## What to ask me if you get stuck

If anything is ambiguous, ask before building. Specifically:
- "Your vault path in `.env` is empty — where is your Obsidian vault?" — before first sync
- "yfinance rate-limited for ticker X — do you want me to add a retry with backoff?"
- "The ticker search returned no results for X — should I try alternate suffixes (.NS, .BO)?"

---

*This prompt was generated as part of the StockBrain project planning session.*
*Version: 2.4 | Date: 2026-05-31 | Changes: local ONNX embeddings via fastembed (dropped OpenAI); tiered models (Haiku signals / Sonnet chat+overview, Opus reserved); yfinance caching+backoff layer (data/cache.py); Chroma list-metadata flattening + delete-before-add; bundled-JSON-first search; prompt caching + API budget caps; dropped SEC EDGAR filings; SEBI + privacy disclosures; scorer unit tests; recharts line-of-closes clarification*
