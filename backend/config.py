"""Central configuration, loaded from .env.

Every tunable — model IDs, paths, API keys — lives here so the rest of the code never
hardcodes a secret or a model snapshot. Reading from a missing .env is fine: the app is
designed to run with no keys at all (data features work; AI features degrade gracefully).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above backend/). Silent if absent.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# Writable data dir for all caches/DB/config. In the packaged app, Electron sets
# STOCKBRAIN_DATA_DIR to the OS user-data folder (the app bundle itself is read-only).
DB_DIR = Path(os.getenv("STOCKBRAIN_DATA_DIR", "").strip() or (_PROJECT_ROOT / "backend" / "db"))
try:
    DB_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass


def bundle_path(rel: str) -> Path:
    """Locate a bundled resource (e.g. the ticker JSONs): under PyInstaller's _MEIPASS
    when frozen, else relative to the project root."""
    return Path(getattr(sys, "_MEIPASS", _PROJECT_ROOT)) / rel

# --- Secrets / optional keys ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "").strip()

# --- Paths ---
VAULT_PATH: str = os.getenv("VAULT_PATH", "").strip()
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "").strip() or str(DB_DIR / "chroma")

# --- Models (defaults match the build brief; override via .env) ---
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5").strip()
SIGNALS_MODEL: str = os.getenv("SIGNALS_MODEL", "claude-haiku-4-5-20251001").strip()
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "claude-sonnet-4-6").strip()
OVERVIEW_MODEL: str = os.getenv("OVERVIEW_MODEL", "claude-sonnet-4-6").strip()

# --- Chat LLM provider ---
# "auto" (default): use Anthropic if a key is set, else a local Ollama if reachable.
# "anthropic" forces Claude; "ollama" forces the local model (keyless, offline).
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3").strip()


def has_anthropic_key() -> bool:
    """True when an Anthropic key is configured, so callers can enable AI paths."""
    return bool(ANTHROPIC_API_KEY)


# --- Runtime app config (vault path chosen in the UI, last sync time) ---
# Stored in a small JSON so a vault picked at runtime survives restarts without editing .env.
import json as _json  # noqa: E402

_APP_CONFIG_PATH = DB_DIR / "app_config.json"


def _read_app_config() -> dict:
    if _APP_CONFIG_PATH.exists():
        try:
            return _json.loads(_APP_CONFIG_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def _write_app_config(data: dict) -> None:
    _APP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _APP_CONFIG_PATH.write_text(_json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def get_vault_path() -> str:
    """Runtime-selected vault path takes precedence over the .env VAULT_PATH."""
    return (_read_app_config().get("vault_path") or VAULT_PATH or "").strip()


def set_vault_path(path: str) -> None:
    cfg = _read_app_config()
    cfg["vault_path"] = path.strip()
    _write_app_config(cfg)


def get_last_synced() -> str | None:
    return _read_app_config().get("last_synced")


def set_last_synced(iso: str) -> None:
    cfg = _read_app_config()
    cfg["last_synced"] = iso
    _write_app_config(cfg)


def get_llm_provider() -> str:
    """Chat provider: a runtime UI override wins over the .env LLM_PROVIDER."""
    return (_read_app_config().get("llm_provider") or LLM_PROVIDER or "auto").lower()


def set_llm_provider(provider: str) -> None:
    cfg = _read_app_config()
    cfg["llm_provider"] = (provider or "auto").lower()
    _write_app_config(cfg)


def get_ollama_model() -> str:
    return _read_app_config().get("ollama_model") or OLLAMA_MODEL


def set_ollama_model(model: str) -> None:
    cfg = _read_app_config()
    cfg["ollama_model"] = model.strip()
    _write_app_config(cfg)
