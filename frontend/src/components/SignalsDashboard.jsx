import { useEffect, useRef, useState } from "react";
import { getSignals, refreshSignals, getSignalsStatus } from "../api.js";
import Reveal from "./Reveal.jsx";
import SignalCard from "./SignalCard.jsx";

const FILTERS = ["ALL", "BUY", "SELL", "WATCH"];

export default function SignalsDashboard({ onOpenStock }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [highOnly, setHighOnly] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    getSignals()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
    return () => clearInterval(pollRef.current);
  }, []);

  async function refresh() {
    setRunning(true);
    setProgress("Starting…");
    try {
      await refreshSignals();
    } catch {
      setRunning(false);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const st = await getSignalsStatus();
        setProgress(st.progress || "Working…");
        if (!st.running) {
          clearInterval(pollRef.current);
          setData(await getSignals());
          setRunning(false);
        }
      } catch {
        clearInterval(pollRef.current);
        setRunning(false);
      }
    }, 2000);
  }

  const signals = data?.signals || [];
  const highCount = signals.filter((s) => s.confidence === "HIGH").length;
  const shown = signals.filter(
    (s) => (filter === "ALL" || s.signal_type === filter) && (!highOnly || s.confidence === "HIGH")
  );

  return (
    <div className="signals-view">
      <Reveal>
        <div className="signals-head">
          <div>
            <h1 className="signals-title">AI Signals</h1>
            <p className="signals-sub">
              {data?.generated_at
                ? `${signals.length} signals · ${highCount} high-confidence · updated ${ageLabel(
                    data.cache_age_minutes
                  )}`
                : "Screening the Nifty 500 for technical + fundamental setups."}
              {data && data.ai_generated === false && signals.length > 0 && (
                <span className="signals-nokey"> · add an API key for AI-written analysis</span>
              )}
            </p>
          </div>
          <button className="btn-primary" onClick={refresh} disabled={running}>
            {running ? <><span className="spinner" /> {progress}</> : "↻ Refresh"}
          </button>
        </div>
      </Reveal>

      {signals.length > 0 && (
        <Reveal>
          <div className="signals-filters">
            {FILTERS.map((f) => (
              <button
                key={f}
                className={`filter-pill ${filter === f ? "active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
            <button
              className={`filter-pill ${highOnly ? "active" : ""}`}
              onClick={() => setHighOnly((v) => !v)}
            >
              High confidence only
            </button>
          </div>
        </Reveal>
      )}

      {loading ? (
        <div className="lazy-loading"><span className="spinner" /> Loading signals…</div>
      ) : signals.length === 0 ? (
        <Reveal>
          <div className="signals-empty panel">
            <h2>No signals yet</h2>
            <p className="muted">
              Run a scan of the Nifty 500 to generate buy / sell / watch signals backed by RSI,
              moving averages, volume and fundamentals.
            </p>
            <button className="btn-primary" onClick={refresh} disabled={running}>
              {running ? <><span className="spinner" /> {progress}</> : "Generate signals"}
            </button>
          </div>
        </Reveal>
      ) : (
        <div className="signals-grid">
          {shown.map((s, i) => (
            <Reveal key={s.ticker} delay={Math.min(i, 8) * 40}>
              <SignalCard signal={s} onOpenStock={onOpenStock} />
            </Reveal>
          ))}
          {shown.length === 0 && <p className="muted">No signals match this filter.</p>}
        </div>
      )}

      <p className="signals-disclaimer">
        StockBrain signals are for research purposes only. Not financial advice. Always do your own
        due diligence before investing.
      </p>
    </div>
  );
}

function ageLabel(mins) {
  if (mins == null) return "just now";
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.floor(mins / 60);
  return `${h}h ago`;
}
