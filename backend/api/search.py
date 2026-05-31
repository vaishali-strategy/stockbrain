"""Search + the single-call stock profile that powers the whole StockPage."""

from __future__ import annotations

from fastapi import APIRouter

from ..data import market, news, overview, search

router = APIRouter(tags=["search"])


@router.get("/search")
def search_endpoint(q: str = "") -> dict:
    """Freeform ticker/company search. e.g. /search?q=reliance"""
    return {"query": q, "results": search.search_ticker(q)}


@router.get("/stock/{ticker}")
def stock_profile(ticker: str, period: str = "3mo") -> dict:
    """Everything the StockPage needs in one call: quote, overview, financials, news, chart.

    Vault note fields are stubbed (vault/RAG lands in a later pass) so the contract is
    already stable for the frontend.
    """
    return {
        "ticker": ticker,
        "quote": market.get_quote(ticker),
        "overview": overview.get_company_overview(ticker),
        "financials": market.get_financials(ticker),
        "news": news.get_news(ticker, limit=5),
        "chart": {"period": period, "ohlcv": market.get_history(ticker, period)},
        "has_vault_notes": False,
        "vault_note_count": 0,
    }
