import { useEffect, useState } from "react";
import { getQuote, formatRupees, formatLargeRupees, formatNumber, formatPct } from "../api.js";

// Compact quote widget. Auto-refreshes every 60s.
export default function StockCard({ ticker, quote: initial }) {
  const [quote, setQuote] = useState(initial);

  useEffect(() => {
    setQuote(initial);
    const id = setInterval(async () => {
      try {
        const q = await getQuote(ticker);
        if (!q.error) setQuote(q);
      } catch {
        /* keep last good quote */
      }
    }, 60000);
    return () => clearInterval(id);
  }, [ticker, initial]);

  if (!quote || quote.error) {
    return <div className="panel error-box">Quote unavailable for {ticker}.</div>;
  }

  const up = (quote.change_pct ?? 0) >= 0;

  return (
    <section className="panel quote-card">
      <div className="quote-price-row">
        <span className="quote-price">{formatRupees(quote.price)}</span>
        <span className={`quote-change ${up ? "pos" : "neg"}`}>{formatPct(quote.change_pct)}</span>
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
