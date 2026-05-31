import { formatLargeRupees } from "../api.js";

export default function FinancialsTable({ financials }) {
  if (!financials) return null;
  const f = financials;

  const rows = [
    ["Revenue (TTM)", formatLargeRupees(f.revenue_ttm), null],
    ["Gross margin", pct(f.gross_margin), sign(f.gross_margin)],
    ["Net margin", pct(f.net_margin), sign(f.net_margin)],
    ["EPS (TTM)", f.eps_ttm != null ? "₹" + f.eps_ttm.toFixed(2) : "—", sign(f.eps_ttm)],
    ["Debt / Equity", f.debt_equity != null ? f.debt_equity.toFixed(2) : "—", null],
  ];

  return (
    <section className="panel">
      <h2 className="panel-title">Financials</h2>
      <table className="fin-table">
        <tbody>
          {rows.map(([label, value, tone]) => (
            <tr key={label}>
              <td className="fin-label">{label}</td>
              <td className={`fin-value ${tone === "pos" ? "pos" : tone === "neg" ? "neg" : ""}`}>
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <a
        className="attribution"
        href="https://finance.yahoo.com"
        target="_blank"
        rel="noreferrer"
      >
        Data via Yahoo Finance ↗
      </a>
    </section>
  );
}

function pct(v) {
  return v == null ? "—" : `${v.toFixed(2)}%`;
}

function sign(v) {
  if (v == null) return null;
  return v >= 0 ? "pos" : "neg";
}
