"""Search + the single-call stock profile that powers the whole StockPage."""

from __future__ import annotations

from fastapi import APIRouter

from ..data import fundamentals, market, news, overview, quality, search, shareholding, technicals

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
        "name": search.company_name(ticker),
        "quote": market.get_quote(ticker),
        "overview": overview.get_company_overview(ticker),
        "financials": market.get_financials(ticker),
        "news": news.get_news(ticker, limit=5),
        "chart": {"period": period, "ohlcv": market.get_history(ticker, period)},
        "has_vault_notes": False,
        "vault_note_count": 0,
    }


@router.get("/stock/{ticker}/fundamentals")
def stock_fundamentals(ticker: str) -> dict:
    """Heavier fundamentals fetched lazily by the StockPage after the fast profile loads:
    quarterly results trend (yfinance), key ratios (yfinance), shareholding (screener.in).
    """
    return {
        "ticker": ticker,
        "quarterly": fundamentals.get_quarterly_results(ticker),
        "ratios": fundamentals.get_key_ratios(ticker),
        "shareholding": shareholding.get_shareholding(ticker),
    }


@router.get("/stock/{ticker}/quality")
def stock_quality(ticker: str) -> dict:
    """Four-layer profitability analysis (earnings quality, moat, capital allocation,
    valuation) + a pre-buy checklist. Heavier (multiple statements + screener) so it's
    fetched lazily and separately from the main profile."""
    return quality.get_quality_analysis(ticker)


@router.get("/stock/{ticker}/technicals")
def stock_technicals(ticker: str) -> dict:
    """Full technical-analysis snapshot: moving averages, oscillators (RSI/MACD/Stochastic/
    ADX), Bollinger Bands, pivot/Fibonacci/support-resistance levels, volume/OBV, the latest
    candlestick pattern, and a synthesized bull/bear rating."""
    return technicals.get_technical_analysis(ticker)
