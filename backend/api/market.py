"""Market data routes — thin wrappers over backend.data.market."""

from __future__ import annotations

from fastapi import APIRouter

from ..data import market, news

router = APIRouter(tags=["market"])


@router.get("/quote/{ticker}")
def quote(ticker: str) -> dict:
    return market.get_quote(ticker)


@router.get("/news/{ticker}")
def ticker_news(ticker: str, limit: int = 5) -> dict:
    return {"ticker": ticker, "news": news.get_news(ticker, limit)}


@router.get("/chart/{ticker}")
def chart(ticker: str, period: str = "3mo") -> dict:
    return {"ticker": ticker, "period": period, "ohlcv": market.get_history(ticker, period)}
