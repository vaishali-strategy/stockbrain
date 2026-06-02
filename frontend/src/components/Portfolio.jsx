import { useCallback, useEffect, useRef, useState } from "react";
import { getQuote, formatRupees, formatLargeRupees, formatPct, isMarketOpen, nowTimeIST } from "../api.js";
import { usePortfolio, addHolding, removeHolding, clearHoldings, parseHoldingsCSV } from "../portfolio.js";
import { useDocumentVisible, useInterval } from "../hooks.js";
import Reveal from "./Reveal.jsx";
import PortfolioAnalysis from "./PortfolioAnalysis.jsx";

const POLL_MS = 30000;

export default function Portfolio({ onOpenStock }) {
  const holdings = usePortfolio();
  const [quotes, setQuotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(nowTimeIST());
  const [importMsg, setImportMsg] = useState("");
  const fileRef = useRef(null);
  const visible = useDocumentVisible();
  const live = isMarketOpen() && visible && holdings.length > 0;

  const tickers = holdings.map((h) => h.ticker).join(",");

  const fetchQuotes = useCallback(
    async (silent = false) => {
      if (holdings.length === 0) {
        setQuotes({});
        setLoading(false);
        return;
      }
      if (!silent) setLoading(true);
      const pairs = await Promise.all(
        holdings.map((h) =>
          getQuote(h.ticker).then((q) => [h.ticker, q]).catch(() => [h.ticker, { error: true }])
        )
      );
      setQuotes(Object.fromEntries(pairs));
      setUpdatedAt(nowTimeIST());
      setLoading(false);
    },
    [tickers] // eslint-disable-line react-hooks/exhaustive-deps
  );

  useEffect(() => {
    fetchQuotes(false);
  }, [fetchQuotes]);
  useInterval(() => fetchQuotes(true), POLL_MS, live);

  // --- derived metrics ---
  let invested = 0, current = 0, dayPnl = 0;
  const rows = holdings.map((h) => {
    const q = quotes[h.ticker];
    const price = q && !q.error ? q.price : null;
    const inv = h.qty * h.avg_price;
    const cur = price != null ? h.qty * price : null;
    const pnl = cur != null ? cur - inv : null;
    const pnlPct = pnl != null && inv ? (pnl / inv) * 100 : null;
    const prev = q && !q.error ? q.previous_close : null;
    const day = price != null && prev != null ? h.qty * (price - prev) : null;
    invested += inv;
    if (cur != null) current += cur;
    if (day != null) dayPnl += day;
    return { h, price, inv, cur, pnl, pnlPct, day };
  });
  const totalPnl = current - invested;
  const totalPnlPct = invested ? (totalPnl / invested) * 100 : 0;

  function onAdd(e) {
    e.preventDefault();
    const f = e.target;
    addHolding({
      ticker: f.ticker.value,
      qty: parseFloat(f.qty.value),
      avg_price: parseFloat(f.avg.value),
    });
    f.reset();
    f.ticker.focus();
  }

  function onImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const { holdings: parsed, skipped, error } = parseHoldingsCSV(String(reader.result));
      if (error) {
        setImportMsg(error);
        return;
      }
      parsed.forEach(addHolding);
      setImportMsg(`Imported ${parsed.length} holding(s)${skipped ? `, skipped ${skipped} row(s)` : ""}.`);
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  return (
    <div className="signals-view">
      <Reveal>
        <div className="signals-head">
          <div>
            <h1 className="signals-title">Portfolio</h1>
            <p className="signals-sub">
              {holdings.length > 0
                ? `${holdings.length} holding${holdings.length > 1 ? "s" : ""}`
                : "Add holdings or import your broker CSV to track live P&L."}
              {live && <span className="wl-live"> · <span className="live-dot" /> Live · {updatedAt}</span>}
            </p>
          </div>
          <div className="pf-actions">
            <button className="btn-ghost" onClick={() => fileRef.current?.click()}>⬆ Import CSV</button>
            <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={onImport} />
            {holdings.length > 0 && (
              <button className="btn-ghost" onClick={() => { if (confirm("Clear all holdings?")) clearHoldings(); }}>Clear</button>
            )}
          </div>
        </div>
      </Reveal>

      {importMsg && <Reveal><div className="chat-banner">{importMsg}</div></Reveal>}

      {/* Summary */}
      {holdings.length > 0 && (
        <Reveal>
          <div className="pf-summary">
            <Summary label="Invested" value={formatLargeRupees(invested)} />
            <Summary label="Current value" value={formatLargeRupees(current)} />
            <Summary label="Total P&L" value={formatRupees(totalPnl)} sub={formatPct(totalPnlPct)} tone={totalPnl >= 0 ? "pos" : "neg"} />
            <Summary label="Day's P&L" value={formatRupees(dayPnl)} tone={dayPnl >= 0 ? "pos" : "neg"} />
          </div>
        </Reveal>
      )}

      {/* Add form */}
      <Reveal>
        <form className="pf-add panel" onSubmit={onAdd}>
          <input name="ticker" placeholder="Symbol (e.g. RELIANCE)" className="searchbar-input" required />
          <input name="qty" type="number" step="any" min="0" placeholder="Qty" className="searchbar-input" required />
          <input name="avg" type="number" step="any" min="0" placeholder="Avg buy ₹" className="searchbar-input" required />
          <button className="btn-primary" type="submit">Add</button>
        </form>
      </Reveal>

      {/* Holdings table */}
      {holdings.length > 0 && (
        <Reveal>
          <section className="panel">
            <div className="table-scroll">
              <table className="data-table pf-table">
                <thead>
                  <tr>
                    <th>Stock</th><th>Qty</th><th>Avg</th><th>LTP</th>
                    <th>Invested</th><th>Current</th><th>P&L</th><th>Day</th><th>Alloc</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(({ h, price, inv, cur, pnl, pnlPct, day }) => (
                    <tr key={h.ticker} className="pf-row" onClick={() => onOpenStock(h.ticker)}>
                      <td className="pf-name"><span className="search-symbol">{h.ticker.replace(/\.(NS|BO)$/, "")}</span></td>
                      <td>{h.qty}</td>
                      <td>{formatRupees(h.avg_price)}</td>
                      <td>{loading && price == null ? "…" : price != null ? formatRupees(price) : "—"}</td>
                      <td>{formatRupees(inv)}</td>
                      <td>{cur != null ? formatRupees(cur) : "—"}</td>
                      <td className={pnl == null ? "" : pnl >= 0 ? "pos" : "neg"}>
                        {pnl != null ? `${formatRupees(pnl)}` : "—"}
                        {pnlPct != null && <span className="pf-pct"> ({formatPct(pnlPct)})</span>}
                      </td>
                      <td className={day == null ? "" : day >= 0 ? "pos" : "neg"}>{day != null ? formatRupees(day) : "—"}</td>
                      <td>{cur != null && current ? `${((cur / current) * 100).toFixed(1)}%` : "—"}</td>
                      <td className="wl-remove">
                        <button title="Remove" onClick={(e) => { e.stopPropagation(); removeHolding(h.ticker); }}>✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </Reveal>
      )}

      {/* Fundamental good/bad grading + news-impact flags (on-demand, cached). */}
      {holdings.length > 0 && (
        <PortfolioAnalysis holdings={holdings} onOpenStock={onOpenStock} />
      )}

      {holdings.length === 0 && (
        <Reveal>
          <div className="signals-empty panel">
            <h2>No holdings yet</h2>
            <p className="muted">Add a position above, or import your broker's holdings CSV. Prices and P&L update live during market hours.</p>
          </div>
        </Reveal>
      )}
    </div>
  );
}

function Summary({ label, value, sub, tone }) {
  return (
    <div className="pf-sum-card">
      <div className="pf-sum-label">{label}</div>
      <div className={`pf-sum-value ${tone || ""}`}>{value}</div>
      {sub && <div className={`pf-sum-sub ${tone || ""}`}>{sub}</div>}
    </div>
  );
}
