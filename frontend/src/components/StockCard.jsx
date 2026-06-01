import { useEffect, useState } from "react";
import {
  getQuote,
  formatRupees,
  formatLargeRupees,
  formatNumber,
  formatPct,
  isMarketOpen,
  nowTimeIST,
} from "../api.js";
import { useDocumentVisible, useInterval } from "../hooks.js";

const POLL_MS = 30000; // refresh the quote every 30s while the market is open

// Compact quote widget with live auto-refresh during market hours.
export default function StockCard({ ticker, quote: initial }) {
  const [quote, setQuote] = useState(initial);
  const [updatedAt, setUpdatedAt] = useState(nowTimeIST());
  const visible = useDocumentVisible();
  const open = isMarketOpen();
  const live = open && visible;

  useEffect(() => {
    setQuote(initial);
    setUpdatedAt(nowTimeIST());
  }, [ticker, initial]);

  async function refresh() {
    try {
      const q = await getQuote(ticker);
      if (!q.error) {
        setQuote(q);
        setUpdatedAt(nowTimeIST());
      }
    } catch {
      /* keep last good quote */
    }
  }

  // Poll only while the market is open and the tab is visible.
  useInterval(refresh, POLL_MS, live);

  if (!quote || quote.error) {
    return <div className="panel error-box">Quote unavailable for {ticker}.</div>;
  }

  const up = (quote.change_pct ?? 0) >= 0;

  return (
    <section className="panel quote-card">
      <div className="quote-price-row">
        <span className="quote-price">{formatRupees(quote.price)}</span>
        <span className={`quote-change ${up ? "pos" : "neg"}`}>{formatPct(quote.change_pct)}</span>
        <span className="quote-live">
          {live ? (
            <><span className="live-dot" /> Live · {updatedAt}</>
          ) : (
            <>Market closed · last close</>
          )}
        </span>
      </div>
      <div className="quote-grid">
        <Metric label="Volume" value={formatNumber(quote.volume)} />
        <Metric label="Market cap" value={formatLargeRupees(quote.market_cap)} />
        <Metric label="P/E" value={quote.pe_ratio ?? "—"} />
        <Metric
          label="52-week range"
          value={`${formatRupees(quote.week52_low)} – ${formatRupees(quote.week52_high)}`}
        />
      </div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}
