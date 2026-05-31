import { useEffect, useState } from "react";
import { getStock } from "../api.js";
import StockCard from "./StockCard.jsx";
import StockChart from "./StockChart.jsx";
import FinancialsTable from "./FinancialsTable.jsx";
import NewsFeed from "./NewsFeed.jsx";

export default function StockPage({ ticker }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getStock(ticker)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load this stock.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
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

  return (
    <div className="stockpage">
      <div className="stockpage-header">
        <h1>{displayTicker}</h1>
        {exchange && <span className="badge">{exchange}</span>}
        {overview?.sector && <span className="chip">{overview.sector}</span>}
      </div>

      <div className="stockpage-grid">
        <div className="stockpage-left">
          <StockCard ticker={ticker} quote={quote} />
          <StockChart ticker={ticker} initial={data.chart} />
          <FinancialsTable financials={financials} />
          <NewsFeed news={data.news} />
        </div>

        <aside className="stockpage-right">
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
              {overview?.employees && <span className="chip">{overview.employees.toLocaleString("en-IN")} employees</span>}
              {overview?.country && <span className="chip">{overview.country}</span>}
              {overview?.website && (
                <a className="chip chip-link" href={overview.website} target="_blank" rel="noreferrer">
                  Website ↗
                </a>
              )}
            </div>
          </section>

          <section className="panel notes-empty">
            <h2 className="panel-title">Your notes</h2>
            <p className="muted">
              Connect your Obsidian vault to save research notes on {displayTicker} and chat over
              them. (Coming in the next build.)
            </p>
          </section>
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
