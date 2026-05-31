import { formatLargeRupees } from "../api.js";

// Quarterly results trend (yfinance): revenue, operating profit, OPM%, net profit, EPS.
export default function QuarterlyResults({ quarterly }) {
  if (!quarterly || !quarterly.available) return null;
  const { quarters, rows } = quarterly;

  const lines = [
    ["Revenue", rows.revenue, "rupees"],
    ["Operating Profit", rows.operating_profit, "rupees"],
    ["OPM %", rows.opm_pct, "pct"],
    ["Net Profit", rows.net_profit, "rupees"],
    ["EPS", rows.eps, "eps"],
  ];

  const fmt = (v, kind) => {
    if (v == null) return "—";
    if (kind === "rupees") return formatLargeRupees(v);
    if (kind === "pct") return `${v.toFixed(1)}%`;
    return "₹" + v.toFixed(2);
  };

  return (
    <section className="panel">
      <h2 className="panel-title">Quarterly Results</h2>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              {quarters.map((q) => (
                <th key={q}>{q}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map(([label, series, kind]) => (
              <tr key={label}>
                <td>{label}</td>
                {series.map((v, i) => (
                  <td key={i}>{fmt(v, kind)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <a className="attribution" href="https://finance.yahoo.com" target="_blank" rel="noreferrer">
        Data via Yahoo Finance ↗
      </a>
    </section>
  );
}
