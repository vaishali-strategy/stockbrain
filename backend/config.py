"""Central configuration, loaded from .env.

Every tunable — model IDs, paths, API keys — lives here so the rest of the code never
hardcodes a secret or a model snapshot. Reading from a missing .env is fine: the app is
designed to run with no keys at all (data features work; AI features degrade gracefully).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above backend/). Silent if absent.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Secrets / optional keys ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "").strip()

# --- Paths ---
VAULT_PATH: str = os.getenv("VAULT_PATH", "").strip()
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./backend/db/chroma").strip()

# --- Models (defaults match the build brief; override via .env) ---
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5").strip()
SIGNALS_MODEL: str = os.getenv("SIGNALS_MODEL", "claude-haiku-4-5-20251001").strip()
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "claude-sonnet-4-6").strip()
OVERVIEW_MODEL: str = os.getenv("OVERVIEW_MODEL", "claude-sonnet-4-6").strip()


def has_anthropic_key() -> bool:
    """True when an Anthropic key is configured, so callers can enable AI paths."""
    return bool(ANTHROPIC_API_KEY)
