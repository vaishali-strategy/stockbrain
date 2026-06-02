"""Portfolio-wide analysis endpoint.

Holdings live client-side (browser localStorage), so the client POSTs them here. We return
a fundamental good/watch/weak verdict per holding (reusing the quality engine) plus a
news-impact flag. Heavy + cached — see ``data.portfolio_analysis``.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..data import portfolio_analysis

router = APIRouter(tags=["portfolio"])


class Holding(BaseModel):
    ticker: str
    name: str | None = None
    qty: float | None = None
    avg_price: float | None = None


class AnalyzeRequest(BaseModel):
    holdings: list[Holding] = []
    force: bool = False


@router.post("/portfolio/analyze")
async def analyze_portfolio(req: AnalyzeRequest) -> dict:
    holdings = [h.model_dump() for h in req.holdings if h.ticker]
    if not holdings:
        return {
            "analyzed_at": None, "engine": "none", "holdings": [],
            "buckets": {"good": [], "watch": [], "weak": []}, "news_to_watch": [],
        }
    return await portfolio_analysis.analyze(holdings, force=req.force)
