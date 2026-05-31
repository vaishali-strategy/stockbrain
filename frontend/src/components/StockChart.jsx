import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { getChart, formatRupees } from "../api.js";

// recharts has no native candlestick — we plot the line of closing prices only.
const PERIODS = [
  ["1W", "1w"],
  ["1M", "1mo"],
  ["3M", "3mo"],
  ["6M", "6mo"],
  ["1Y", "1y"],
];

export default function StockChart({ ticker, initial }) {
  const [period, setPeriod] = useState(initial?.period || "3mo");
  const [ohlcv, setOhlcv] = useState(initial?.ohlcv || []);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Use the data already loaded with the page for its period; fetch only on change.
    if (period === initial?.period) {
      setOhlcv(initial.ohlcv || []);
      return;
    }
    let cancelled = false;
    setLoading(true);
    getChart(ticker, period)
      .then((d) => {
        if (!cancelled) setOhlcv(d.ohlcv || []);
      })
      .catch(() => {
        if (!cancelled) setOhlcv([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker, period, initial]);

  const closes = ohlcv.map((d) => d.close).filter((c) => c != null);
  const up = closes.length >= 2 ? closes[closes.length - 1] >= closes[0] : true;
  const color = up ? "var(--pos)" : "var(--neg)";

  return (
    <section className="panel chart-panel">
      <div className="chart-header">
        <h2 className="panel-title">Price</h2>
        <div className="period-toggle">
          {PERIODS.map(([label, value]) => (
            <button
              key={value}
              className={period === value ? "active" : ""}
              onClick={() => setPeriod(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="chart-empty">Loading…</div>
      ) : ohlcv.length === 0 ? (
        <div className="chart-empty">No price data.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={ohlcv} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-dim)" }} minTickGap={40} />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: "var(--text-dim)" }}
              width={64}
              tickFormatter={(v) => "₹" + Math.round(v).toLocaleString("en-IN")}
            />
            <Tooltip content={<ChartTooltip />} />
            <Line type="monotone" dataKey="close" stroke={color} dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tt-date">{label}</div>
      <div>O {formatRupees(d.open)}</div>
      <div>H {formatRupees(d.high)}</div>
      <div>L {formatRupees(d.low)}</div>
      <div className="tt-close">C {formatRupees(d.close)}</div>
      <div className="tt-vol">Vol {d.volume ? Number(d.volume).toLocaleString("en-IN") : "—"}</div>
    </div>
  );
}
