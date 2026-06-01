// Four-layer profitability analysis: earnings quality → moat → capital allocation →
// valuation, plus the pre-buy checklist. Mirrors the analyst framework.

const STATUS = {
  pass: { icon: "✓", cls: "chk-pass" },
  warn: { icon: "!", cls: "chk-warn" },
  fail: { icon: "✕", cls: "chk-fail" },
  info: { icon: "○", cls: "chk-info" },
};

const fmtX = (v) => (v == null ? "—" : `${v}×`);
const fmtPct = (v) => (v == null ? "—" : `${v}%`);
const fmtNum = (v) => (v == null ? "—" : v);

export default function ProfitabilityAnalysis({ quality }) {
  if (!quality) return null;
  const { earnings_quality: eq, moat, capital_allocation: cap, valuation: val, checklist } = quality;

  return (
    <section className="panel quality-panel">
      <h2 className="panel-title">
        Profitability Analysis
        <span className="quality-score">
          {quality.checklist_score}/{quality.checklist_total} checks pass
        </span>
      </h2>

      {/* Layer 1 */}
      <Layer n="1" title="Quality of Earnings" q="Is the profit real cash?">
        <Metric label="Cash conversion (OCF ÷ Net income)" value={fmtX(eq.cash_conversion)}
          tone={eq.cash_conversion >= 1 ? "good" : eq.cash_conversion >= 0.8 ? "warn" : "bad"}
          hint="≥ 1× means profit turns into real cash" />
        <Metric label="Gross-margin trend" value={eq.gross_margin_direction || "—"}
          tone={["expanding", "stable"].includes(eq.gross_margin_direction) ? "good" : "warn"} />
        <Metric label="Revenue CAGR" value={fmtPct(eq.revenue_cagr)} />
        <Metric label="Receivables vs revenue" value={eq.receivables_outpacing_revenue ? "outpacing ⚠" : "in line"}
          tone={eq.receivables_outpacing_revenue ? "warn" : "good"}
          hint="Receivables growing faster than sales can flag uncollected revenue" />
      </Layer>

      {/* Layer 2 */}
      <Layer n="2" title="Competitive Moat" q="Why can't a rival copy this?">
        <Metric label="ROCE (latest)" value={fmtPct(moat.roce_latest)}
          tone={(moat.roce_latest ?? 0) >= 15 ? "good" : "warn"} />
        <Metric label="ROCE 5-yr average" value={fmtPct(moat.roce_avg_5y)}
          tone={(moat.roce_avg_5y ?? 0) >= 15 ? "good" : "warn"} />
        <Metric label="Years ROCE ≥ 15%" value={moat.years_total ? `${moat.years_above_15}/${moat.years_total}` : "—"}
          tone={moat.roce_consistent_15 ? "good" : "warn"}
          hint="Consistently high ROCE is the practical moat test" />
        {moat.roce_available && moat.roce_history?.length > 0 && (
          <RoceSpark history={moat.roce_history} years={moat.roce_years} />
        )}
      </Layer>

      {/* Layer 3 */}
      <Layer n="3" title="Capital Allocation" q="Does management deploy profit well?">
        <Metric label="Debt / Equity" value={fmtX(cap.debt_equity_x)}
          tone={cap.debt_equity_x == null ? null : cap.debt_equity_x < 1 ? "good" : cap.debt_equity_x < 2 ? "warn" : "bad"} />
        <Metric label="Reinvestment rate" value={fmtPct(cap.reinvestment_rate)}
          hint="Share of profit ploughed back vs paid out" />
        <Metric label="Dividend yield" value={fmtPct(cap.dividend_yield)} />
        <Metric label="Promoter holding" value={cap.promoter_holding != null ? `${cap.promoter_holding}% (${cap.promoter_trend || "—"})` : "—"}
          tone={["rising", "stable"].includes(cap.promoter_trend) ? "good" : cap.promoter_trend === "falling" ? "warn" : null} />
      </Layer>

      {/* Layer 4 */}
      <Layer n="4" title="Valuation" q="Are you paying a fair price?">
        <Metric label="P/E" value={fmtNum(val.pe_ratio)} hint="Only meaningful vs the stock's own history & peers" />
        <Metric label="PEG (P/E ÷ growth)" value={fmtNum(val.peg_ratio)}
          tone={val.peg_ratio == null ? null : val.peg_ratio < 1 ? "good" : val.peg_ratio < 2 ? "warn" : "bad"}
          hint="< 1 can mean growth is cheaply priced" />
        <Metric label="EV / EBITDA" value={fmtNum(val.ev_ebitda)} hint="Better than P/E for capital-heavy firms" />
        <Metric label="Price / Free cash flow" value={fmtNum(val.price_to_fcf)} hint="The most honest valuation metric" />
      </Layer>

      {/* Checklist */}
      <div className="quality-checklist">
        <h3 className="quality-sub">Pre-buy checklist</h3>
        {checklist.map((c, i) => {
          const s = STATUS[c.status] || STATUS.info;
          return (
            <div key={i} className="chk-item">
              <span className={`chk-icon ${s.cls}`}>{s.icon}</span>
              <div>
                <div className="chk-label">{c.label}</div>
                <div className="chk-detail">{c.detail}</div>
              </div>
            </div>
          );
        })}
        <p className="quality-foot">
          ○ items need your own judgment — the app won't fake a number it can't compute.
        </p>
      </div>
    </section>
  );
}

function Layer({ n, title, q, children }) {
  return (
    <div className="quality-layer">
      <div className="layer-head">
        <span className="layer-num">{n}</span>
        <div>
          <div className="layer-title">{title}</div>
          <div className="layer-q">{q}</div>
        </div>
      </div>
      <div className="layer-metrics">{children}</div>
    </div>
  );
}

function Metric({ label, value, tone, hint }) {
  return (
    <div className="qmetric" title={hint || ""}>
      <span className="qmetric-label">{label}</span>
      <span className={`qmetric-value ${tone ? `tone-${tone}` : ""}`}>{value}</span>
    </div>
  );
}

function RoceSpark({ history, years }) {
  const vals = history.map((v) => (v == null ? 0 : v));
  const max = Math.max(...vals, 15);
  return (
    <div className="roce-spark">
      {vals.map((v, i) => (
        <div
          key={i}
          className={`roce-bar ${v >= 15 ? "above" : "below"}`}
          style={{ height: `${Math.max((v / max) * 100, 3)}%` }}
          title={`${years?.[i] || ""}: ${history[i] ?? "—"}%`}
        />
      ))}
      <span className="roce-spark-label">ROCE %, last {vals.length}y · 15% line</span>
    </div>
  );
}
