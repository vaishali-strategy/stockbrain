// Key ratios grid (yfinance). Renders only the values that are available.
export default function KeyRatios({ ratios }) {
  if (!ratios) return null;

  const items = [
    ["ROE", pct(ratios.roe)],
    ["ROCE", pct(ratios.roce)],
    ["Book Value", ratios.book_value != null ? "₹" + round(ratios.book_value) : null],
    ["P/B", num(ratios.price_to_book)],
    ["P/E", num(ratios.pe_ratio)],
    ["Div Yield", pct(ratios.dividend_yield)],
    ["Rev Growth", pct(ratios.revenue_growth_yoy)],
    ["EPS Growth", pct(ratios.earnings_growth_yoy)],
    ["Rev CAGR", pct(ratios.revenue_cagr_3y)],
  ].filter(([, v]) => v != null);

  if (items.length === 0) return null;

  return (
    <section className="panel">
      <h2 className="panel-title">Key Ratios</h2>
      <div className="ratios-grid">
        {items.map(([label, value]) => (
          <div className="ratio" key={label}>
            <div className="ratio-label">{label}</div>
            <div className="ratio-value">{value}</div>
          </div>
        ))}
      </div>
      <a className="attribution" href="https://finance.yahoo.com" target="_blank" rel="noreferrer">
        Data via Yahoo Finance · ROCE/CAGR computed ↗
      </a>
    </section>
  );
}

const pct = (v) => (v == null ? null : `${v.toFixed(2)}%`);
const num = (v) => (v == null ? null : v.toFixed(2));
const round = (v) => Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
