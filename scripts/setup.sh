#!/usr/bin/env bash
# One-command setup for StockBrain. Re-runnable (idempotent).
set -e

cd "$(dirname "$0")/.."
echo "▸ Setting up StockBrain in $(pwd)"

# --- Python backend ---
if [ ! -d ".venv" ]; then
  echo "▸ Creating Python virtualenv (.venv)"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "▸ Installing Python dependencies (this pulls chromadb + fastembed; first run is slow)"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# --- Frontend / Electron ---
echo "▸ Installing Node dependencies"
npm install

# --- Config ---
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "▸ Created .env (optional: add ANTHROPIC_API_KEY for cloud AI; otherwise local Ollama is used)"
fi

# --- Bundled data: ticker universes for search + signals ---
echo "▸ Fetching ticker lists (Nifty 500 for search, Nifty 100 for signals)"
python scripts/fetch_nifty500.py || echo "  (Nifty 500 fetch failed — bundled fallback will be used)"
python scripts/fetch_nifty100.py || echo "  (Nifty 100 fetch failed — bundled fallback will be used)"

# --- Example vault so RAG chat has something to retrieve ---
echo "▸ Seeding example Obsidian vault"
python scripts/seed_vault.py

cat <<'EOF'

✓ Setup complete.

  Run in the browser:   npm run dev      → http://localhost:5173
  Run as a desktop app: npm run app

  Optional:
    • Add ANTHROPIC_API_KEY to .env for the best chat/overview quality, or
    • run a local model for free, offline AI:  ollama run llama3
EOF
