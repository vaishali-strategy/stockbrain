"""Fetch the Nifty 500 constituent list and bundle it for offline ticker search.

The app's search is offline-first: it fuzzy-matches user queries against
``backend/data/nifty500_tickers.json`` rather than hitting a flaky network API at
runtime. This script (run once during setup) produces that file.

NSE's public CSV blocks bare/non-browser requests, so we send browser-like headers and
prime the session with a cookie. If the download fails for any reason, we fall back to a
hardcoded top-50 list so setup never breaks and search still works for the big names.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

# CSV of Nifty 500 constituents published by NSE.
NSE_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"

# Where the bundled list lives — read by backend/data/search.py at runtime.
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "nifty500_tickers.json"

# Browser-like headers; NSE rejects requests without them.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/csv,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# Fallback: top Nifty names so search works even if the NSE download fails.
# (Company Name, NSE symbol, sector) — symbol gets the .NS suffix.
_FALLBACK_TOP = [
    ("Reliance Industries Ltd.", "RELIANCE", "Energy"),
    ("Tata Consultancy Services Ltd.", "TCS", "Information Technology"),
    ("HDFC Bank Ltd.", "HDFCBANK", "Financial Services"),
    ("ICICI Bank Ltd.", "ICICIBANK", "Financial Services"),
    ("Infosys Ltd.", "INFY", "Information Technology"),
    ("Bharti Airtel Ltd.", "BHARTIARTL", "Telecommunication"),
    ("State Bank of India", "SBIN", "Financial Services"),
    ("Hindustan Unilever Ltd.", "HINDUNILVR", "Fast Moving Consumer Goods"),
    ("ITC Ltd.", "ITC", "Fast Moving Consumer Goods"),
    ("Larsen & Toubro Ltd.", "LT", "Construction"),
    ("Kotak Mahindra Bank Ltd.", "KOTAKBANK", "Financial Services"),
    ("Axis Bank Ltd.", "AXISBANK", "Financial Services"),
    ("Bajaj Finance Ltd.", "BAJFINANCE", "Financial Services"),
    ("Asian Paints Ltd.", "ASIANPAINT", "Consumer Durables"),
    ("Maruti Suzuki India Ltd.", "MARUTI", "Automobile and Auto Components"),
    ("Sun Pharmaceutical Industries Ltd.", "SUNPHARMA", "Healthcare"),
    ("Titan Company Ltd.", "TITAN", "Consumer Durables"),
    ("HCL Technologies Ltd.", "HCLTECH", "Information Technology"),
    ("NTPC Ltd.", "NTPC", "Power"),
    ("Tata Motors Ltd.", "TATAMOTORS", "Automobile and Auto Components"),
    ("Power Grid Corporation of India Ltd.", "POWERGRID", "Power"),
    ("Wipro Ltd.", "WIPRO", "Information Technology"),
    ("UltraTech Cement Ltd.", "ULTRACEMCO", "Construction Materials"),
    ("Nestle India Ltd.", "NESTLEIND", "Fast Moving Consumer Goods"),
    ("Oil & Natural Gas Corporation Ltd.", "ONGC", "Energy"),
    ("Mahindra & Mahindra Ltd.", "M&M", "Automobile and Auto Components"),
    ("Tata Steel Ltd.", "TATASTEEL", "Metals & Mining"),
    ("JSW Steel Ltd.", "JSWSTEEL", "Metals & Mining"),
    ("Adani Enterprises Ltd.", "ADANIENT", "Metals & Mining"),
    ("Adani Ports and SEZ Ltd.", "ADANIPORTS", "Services"),
    ("Coal India Ltd.", "COALINDIA", "Metals & Mining"),
    ("Bajaj Finserv Ltd.", "BAJAJFINSV", "Financial Services"),
    ("HDFC Life Insurance Company Ltd.", "HDFCLIFE", "Financial Services"),
    ("SBI Life Insurance Company Ltd.", "SBILIFE", "Financial Services"),
    ("Grasim Industries Ltd.", "GRASIM", "Construction Materials"),
    ("Dr. Reddy's Laboratories Ltd.", "DRREDDY", "Healthcare"),
    ("Cipla Ltd.", "CIPLA", "Healthcare"),
    ("Tech Mahindra Ltd.", "TECHM", "Information Technology"),
    ("Eicher Motors Ltd.", "EICHERMOT", "Automobile and Auto Components"),
    ("Britannia Industries Ltd.", "BRITANNIA", "Fast Moving Consumer Goods"),
    ("Hindalco Industries Ltd.", "HINDALCO", "Metals & Mining"),
    ("Divi's Laboratories Ltd.", "DIVISLAB", "Healthcare"),
    ("Hero MotoCorp Ltd.", "HEROMOTOCO", "Automobile and Auto Components"),
    ("Bajaj Auto Ltd.", "BAJAJ-AUTO", "Automobile and Auto Components"),
    ("Apollo Hospitals Enterprise Ltd.", "APOLLOHOSP", "Healthcare"),
    ("IndusInd Bank Ltd.", "INDUSINDBK", "Financial Services"),
    ("Tata Consumer Products Ltd.", "TATACONSUM", "Fast Moving Consumer Goods"),
    ("Shriram Finance Ltd.", "SHRIRAMFIN", "Financial Services"),
    ("BPCL", "BPCL", "Energy"),
    ("LTIMindtree Ltd.", "LTIM", "Information Technology"),
]


def _parse_nse_csv(text: str) -> list[dict]:
    """Parse NSE's CSV. Columns: Company Name, Industry, Symbol, Series, ISIN Code."""
    import csv
    import io

    rows: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        symbol = (row.get("Symbol") or "").strip()
        name = (row.get("Company Name") or "").strip()
        if not symbol or not name:
            continue
        rows.append(
            {
                "ticker": f"{symbol}.NS",
                "name": name,
                "sector": (row.get("Industry") or "").strip(),
                "series": (row.get("Series") or "EQ").strip(),
            }
        )
    return rows


def _fallback_rows() -> list[dict]:
    return [
        {"ticker": f"{symbol}.NS", "name": name, "sector": sector, "series": "EQ"}
        for (name, symbol, sector) in _FALLBACK_TOP
    ]


def fetch() -> list[dict]:
    """Return the ticker list, preferring the live NSE CSV, else the bundled fallback."""
    try:
        session = requests.Session()
        session.headers.update(_HEADERS)
        # Prime cookies by touching the homepage first (NSE sets anti-bot cookies).
        session.get("https://www.nseindia.com", timeout=10)
        resp = session.get(NSE_CSV_URL, timeout=20)
        resp.raise_for_status()
        rows = _parse_nse_csv(resp.text)
        if len(rows) >= 50:
            print(f"Downloaded {len(rows)} Nifty 500 constituents from NSE.")
            return rows
        print(f"NSE returned only {len(rows)} rows — using bundled fallback instead.")
    except Exception as exc:  # noqa: BLE001 — any failure should fall back, never crash setup.
        print(f"NSE download failed ({exc}). Using bundled top-50 fallback.")
    return _fallback_rows()


def main() -> int:
    rows = fetch()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} tickers to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
