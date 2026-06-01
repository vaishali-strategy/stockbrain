import { useEffect, useState, useId } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { getChart, formatRupees } from "../api.js";

// Compact share-volume formatter for the axis (Cr / L / K).
function fmtVol(v) {
  if (v == null) return "—";
  if (v >= 1e7) return (v / 1e7).toFixed(1) + "Cr";
  if (v >= 1e5) return (v / 1e5).toFixed(1) + "L";
  if (v >= 1e3) return (v / 1e3).toFixed(0) + "K";
  return String(v);
}

// recharts has no native candlestick — we plot a glowing gradient area of closing prices.
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
  const uid = useId().replace(/:/g, ""); // unique gradient/filter ids per instance

  useEffect(() => {
    if (period === initial?.period) {
      setOhlcv(initial.ohlcv || []);
      return;
    }
    let cancelled = false;
    setLoading(true);
    getChart(ticker, period)
      .then((d) => !cancelled && setOhlcv(d.ohlcv || []))
      .catch(() => !cancelled && setOhlcv([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [ticker, period, initial]);

  const closes = ohlcv.map((d) => d.close).filter((c) => c != null);
  const up = closes.length >= 2 ? closes[closes.length - 1] >= closes[0] : true;
  const color = up ? "#2fe6a8" : "#ff6b8b";

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
        <ResponsiveContainer width="100%" height={290}>
          <AreaChart data={ohlcv} margin={{ top: 10, right: 8, left: 8, bottom: 0 }}>
            <defs>
              <linearGradient id={`fill-${uid}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
              <filter id={`glow-${uid}`} x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3.5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6f6b91" }} minTickGap={42} tickLine={false} axisLine={false} />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#6f6b91" }}
              width={62}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => "₹" + Math.round(v).toLocaleString("en-IN")}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgba(255,255,255,0.2)" }} />
            <Area
              type="monotone"
              dataKey="close"
              stroke={color}
              strokeWidth={2.4}
              fill={`url(#fill-${uid})`}
              filter={`url(#glow-${uid})`}
              isAnimationActive={false}
              dot={false}
              activeDot={{ r: 5, fill: color, stroke: "#fff", strokeWidth: 1.5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {!loading && ohlcv.length > 0 && (
        <>
          <div className="chart-subtitle">Volume</div>
          <ResponsiveContainer width="100%" height={96}>
            <BarChart data={ohlcv} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="3 6" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6f6b91" }} minTickGap={42} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fontSize: 11, fill: "#6f6b91" }}
                width={62}
                tickLine={false}
                axisLine={false}
                tickFormatter={fmtVol}
              />
              <Tooltip content={<VolumeTooltip />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
              <Bar dataKey="volume" isAnimationActive={false} radius={[2, 2, 0, 0]}>
                {ohlcv.map((d, i) => {
                  // Green when the day closed up vs its open, red when it closed down.
                  const upDay = d.close != null && d.open != null ? d.close >= d.open : true;
                  return <Cell key={i} fill={upDay ? "rgba(47,230,168,0.55)" : "rgba(255,107,139,0.55)"} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </section>
  );
}

function VolumeTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const v = payload[0].payload.volume;
  return (
    <div className="chart-tooltip">
      <div className="tt-date">{label}</div>
      <div>Vol {v != null ? Number(v).toLocaleString("en-IN") : "—"}</div>
    </div>
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
