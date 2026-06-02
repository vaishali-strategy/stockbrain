import { useState } from "react";
import { analyzePortfolio, timeAgo } from "../api.js";
import Reveal from "./Reveal.jsx";

// Fundamental verdict → display chrome. Reuses the global .pos/.neg colour classes.
const VERDICT_META = {
  good: { label: "Good", cls: "pos", icon: "✓" },
  watch: { label: "Watch", cls: "warn", icon: "•" },
  weak: { label: "Needs review", cls: "neg", icon: "✗" },
};

const ENGINE_LABEL = {
  claude: "Claude",
  ollama: "local model",
  heuristic: "keyword heuristic",
  none: "—",
};

// In Electron, open links in the system browser; in the browser, a normal new tab.
function openExternal(url) {
  if (!url) return;
  if (window.electronAPI?.openExternal) window.electronAPI.openExternal(url);
  else window.open(url, "_blank", "noopener");
}

export default function PortfolioAnalysis({ holdings, onOpenStock }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run(force = false) {
    setLoading(true);
    setError("");
    try {
      // Only the fields the backend needs — verdict/news key off the ticker.
      const payload = holdings.map((h) => ({ ticker: h.ticker, name: h.name }));
      setData(await analyzePortfolio(payload, force));
    } catch {
      setError("Analysis failed. Make sure the backend is running, then try again.");
    } finally {
      setLoading(false);
    }
  }

  // Group holdings by fundamental verdict for the good/watch/weak sections.
  const grouped = { good: [], watch: [], weak: [] };
  (data?.holdings || []).forEach((h) => {
    const v = h.fundamental?.verdict || "watch";
    (grouped[v] || grouped.watch).push(h);
  });
  const newsItems = (data?.holdings || []).filter((h) => h.news?.actionable);

  return (
    <Reveal>
      <section className="panel pf-analysis">
        <div className="pf-an-bar">
          <div>
            <h2 className="panel-title">Holdings analysis</h2>
            <p className="muted pf-an-sub">
              {data
                ? `Fundamentals + news · via ${ENGINE_LABEL[data.engine] || data.engine} · ${timeAgo(data.analyzed_at) || "just now"}`
                : "Grade each holding's fundamentals and flag news that could move your positions."}
            </p>
          </div>
          <div className="pf-actions">
            {data ? (
              <button className="btn-ghost" onClick={() => run(true)} disabled={loading}>
                {loading ? <><span className="spinner" /> Re-analyzing…</> : "Re-analyze"}
              </button>
            ) : (
              <button className="btn-primary" onClick={() => run(false)} disabled={loading}>
                {loading ? <><span className="spinner" /> Analyzing…</> : "⟳ Analyze portfolio"}
              </button>
            )}
          </div>
        </div>

        {loading && !data && (
          <div className="lazy-loading">
            <span className="spinner" /> Analyzing {holdings.length} holding{holdings.length > 1 ? "s" : ""}… this can take up to a minute.
          </div>
        )}
        {error && <div className="chat-banner">{error}</div>}

        {data && (
          <>
            {["good", "watch", "weak"].map((v) =>
              grouped[v].length ? (
                <div key={v} className="pf-an-group">
                  <h3 className={`pf-an-head ${VERDICT_META[v].cls}`}>
                    {VERDICT_META[v].icon} {VERDICT_META[v].label} ({grouped[v].length})
                  </h3>
                  <div className="pf-an-cards">
                    {grouped[v].map((h) => {
                      const note = h.fundamental?.concerns?.[0] || h.fundamental?.strengths?.[0];
                      return (
                        <button key={h.ticker} className="pf-an-card" onClick={() => onOpenStock(h.ticker)}>
                          <div className="pf-an-card-top">
                            <span className="search-symbol">{h.ticker.replace(/\.(NS|BO)$/, "")}</span>
                            <span className={`pf-an-pill ${VERDICT_META[v].cls}`}>
                              {h.fundamental?.score}/{h.fundamental?.total}
                            </span>
                          </div>
                          {note && <div className="pf-an-reason">{note.label}</div>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null
            )}

            <div className="pf-an-group">
              <h3 className="pf-an-head">News to watch ({newsItems.length})</h3>
              {newsItems.length === 0 ? (
                <p className="muted">No notable buy/sell-moving news across your holdings right now.</p>
              ) : (
                <ul className="pf-news-list">
                  {newsItems.map((h) => (
                    <li key={h.ticker} className="pf-news-item">
                      <div className="pf-news-row">
                        <span className={`pf-news-stance ${h.news.stance === "bearish" ? "neg" : "pos"}`}>
                          {h.news.stance === "bearish" ? "⚠" : "✓"} {h.ticker.replace(/\.(NS|BO)$/, "")}
                        </span>
                        <span className="pf-news-why">{h.news.rationale}</span>
                      </div>
                      {h.news.top?.length > 0 && (
                        <div className="pf-news-heads">
                          {h.news.top.map((t, i) => (
                            <button key={t.url || i} className="pf-news-head" onClick={() => openExternal(t.url)}>
                              {t.title} <span className="news-ext">↗</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <p className="signals-disclaimer">
              Research only — not investment advice. Fundamental grades and news reads are
              automated aids; always do your own due diligence before acting.
            </p>
          </>
        )}
      </section>
    </Reveal>
  );
}
