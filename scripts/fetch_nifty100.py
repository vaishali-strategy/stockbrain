"""Fetch the Nifty 100 constituent list for the AI signals universe.

The signals screener scans the Nifty 100 (not the full 500) — it's a diverse, liquid,
sector-spread set that produces a real BUY/SELL/WATCH mix and keeps refreshes quick.

Reuses the NSE download + browser-header + cookie-priming logic from fetch_nifty500.py.
Falls back to that script's curated top-50 if NSE is unreachable, so setup never breaks.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import requests

# Load helpers from the sibling fetch_nifty500.py without needing a package.
_F5_PATH = Path(__file__).resolve().parent / "fetch_nifty500.py"
_spec = importlib.util.spec_from_file_location("fetch_nifty500", _F5_PATH)
_f5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f5)

NSE_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "nifty100_tickers.json"


def fetch() -> list[dict]:
    try:
        session = requests.Session()
        session.headers.update(_f5._HEADERS)
        session.get("https://www.nseindia.com", timeout=10)  # prime anti-bot cookies
        resp = session.get(NSE_CSV_URL, timeout=20)
        resp.raise_for_status()
        rows = _f5._parse_nse_csv(resp.text)
        if len(rows) >= 50:
            print(f"Downloaded {len(rows)} Nifty 100 constituents from NSE.")
            return rows
        print(f"NSE returned only {len(rows)} rows — using bundled fallback instead.")
    except Exception as exc:  # noqa: BLE001
        print(f"NSE download failed ({exc}). Using bundled fallback (top 50).")
    return _f5._fallback_rows()


def main() -> int:
    rows = fetch()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} tickers to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
