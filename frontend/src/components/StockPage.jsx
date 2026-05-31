import { useEffect, useState } from "react";
import { getStock, getFundamentals } from "../api.js";
import Reveal from "./Reveal.jsx";
import StockCard from "./StockCard.jsx";
import StockChart from "./StockChart.jsx";
import KeyRatios from "./KeyRatios.jsx";
import QuarterlyResults from "./QuarterlyResults.jsx";
import FinancialsTable from "./FinancialsTable.jsx";
import ShareholdingPattern from "./ShareholdingPattern.jsx";
import NewsFeed from "./NewsFeed.jsx";

export default function StockPage({ ticker }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Heavier fundamentals (quarterly, ratios, shareholding) load separately so the
  // fast profile renders immediately.
  const [fund, setFund] = useState(null);
  const [fundLoading, setFundLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setFund(null);
    setFundLoading(true);

    getStock(ticker)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError("Could not load this stock."))
      .finally(() => !cancelled && setLoading(false));

    getFundamentals(ticker)
      .then((d) => !cancelled && setFund(d))
      .catch(() => !cancelled && setFund(null))
      .finally(() => !cancelled && setFundLoading(false));

    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (loading) return <StockSkeleton />;
  if (error) return <div className="error-box">{error}</div>;
  if (!data) return null;

  const { quote, overview, financials } = data;
  const displayTicker = ticker.replace(/\.(NS|BO)$/, "");
  const exchange = ticker.endsWith(".NS") ? "NSE" : ticker.endsWith(".BO") ? "BSE" : "";

  const hasFund =
    fund &&
    (fund.quarterly?.available || fund.shareholding?.available || fund.ratios);

  return (
    <div className="stockpage">
      <Reveal>
        <div className="stockpage-header">
          <h1>{displayTicker}</h1>
          {exchange && <span className="badge">{exchange}</span>}
          {overview?.sector && <span className="chip">{overview.sector}</span>}
        </div>
      </Reveal>

      <div className="stockpage-grid">
        <div className="stockpage-left">
          <Reveal><StockCard ticker={ticker} quote={quote} /></Reveal>
          <Reveal delay={60}><StockChart ticker={ticker} initial={data.chart} /></Reveal>

          {fundLoading && !hasFund && (
            <Reveal>
              <section className="panel">
                <div className="lazy-loading">
                  <span className="spinner" /> Loading fundamentals…
                </div>
              </section>
            </Reveal>
          )}

          {fund?.ratios && <Reveal><KeyRatios ratios={fund.ratios} /></Reveal>}
          {fund?.quarterly?.available && (
            <Reveal><QuarterlyResults quarterly={fund.quarterly} /></Reveal>
          )}
          <Reveal><FinancialsTable financials={financials} /></Reveal>
          {fund?.shareholding?.available && (
            <Reveal><ShareholdingPattern shareholding={fund.shareholding} /></Reveal>
          )}
          <Reveal><NewsFeed news={data.news} /></Reveal>
        </div>

        <aside className="stockpage-right">
          <Reveal delay={40}>
            <section className="panel">
              <h2 className="panel-title">
                Overview
                {overview?.ai_generated ? (
                  <span className="tag tag-ai">AI</span>
                ) : (
                  <span className="tag" title="Source: Yahoo Finance">Yahoo</span>
                )}
              </h2>
              <div className="overview-text">
                {(overview?.summary || "No overview available.")
                  .split(/\n\n+/)
                  .map((p, i) => (
                    <p key={i}>{p}</p>
                  ))}
              </div>
              <div className="overview-chips">
                {overview?.industry && <span className="chip">{overview.industry}</span>}
                {overview?.employees && (
                  <span className="chip">{overview.employees.toLocaleString("en-IN")} employees</span>
                )}
                {overview?.country && <span className="chip">{overview.country}</span>}
                {overview?.website && (
                  <a className="chip chip-link" href={overview.website} target="_blank" rel="noreferrer">
                    Website ↗
                  </a>
                )}
              </div>
            </section>
          </Reveal>

          <Reveal delay={120}>
            <section className="panel notes-empty">
              <h2 className="panel-title">Your notes</h2>
              <p className="muted">
                Connect your Obsidian vault to save research notes on {displayTicker} and chat over
                them. (Coming in the next build.)
              </p>
            </section>
          </Reveal>
        </aside>
      </div>
    </div>
  );
}

function StockSkeleton() {
  return (
    <div className="stockpage">
      <div className="skeleton skeleton-title" />
      <div className="stockpage-grid">
        <div className="stockpage-left">
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-chart" />
          <div className="skeleton skeleton-card" />
        </div>
        <div className="stockpage-right">
          <div className="skeleton skeleton-panel" />
        </div>
      </div>
    </div>
  );
}
