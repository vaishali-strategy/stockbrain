import { formatRupees, formatPct } from "../api.js";

const SIGNAL_CLASS = { BUY: "sig-buy", SELL: "sig-sell", WATCH: "sig-watch" };
const CONF_CLASS = { HIGH: "conf-high", MEDIUM: "conf-med", LOW: "conf-low" };

export default function SignalCard({ signal, onOpenStock }) {
  const s = signal;
  const symbol = s.ticker.replace(/\.(NS|BO)$/, "");
  const exchange = s.ticker.endsWith(".NS") ? "NSE" : s.ticker.endsWith(".BO") ? "BSE" : "";
  const up = (s.change_pct_today ?? 0) >= 0;

  const tech = [
    s.rsi != null && `RSI ${Math.round(s.rsi)}`,
    s.volume_ratio != null && `Vol ${s.volume_ratio}×`,
    s.vs_50dma != null && `${s.vs_50dma > 0 ? "+" : ""}${s.vs_50dma}% vs 50DMA`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="panel signal-card">
      <div className="sig-top">
        <div className="sig-id">
          <span className="search-symbol">{symbol}</span>
          {exchange && <span className="sig-exch">{exchange}</span>}
        </div>
        <span className={`sig-badge ${SIGNAL_CLASS[s.signal_type]}`}>{s.signal_type}</span>
      </div>

      <div className="sig-name">
        {s.display_name}
        {s.vault_has_notes && <span className="sig-notes" title="You have notes on this">📓</span>}
      </div>

      <div className="sig-price-row">
        <span className="sig-price">{formatRupees(s.current_price)}</span>
        {s.change_pct_today != null && (
          <span className={up ? "pos" : "neg"}>{formatPct(s.change_pct_today)}</span>
        )}
        <span className={`conf-dot ${CONF_CLASS[s.confidence]}`} title={`${s.confidence} confidence`} />
        <span className="conf-label">{s.confidence}</span>
      </div>

      {tech && <div className="sig-tech">{tech}</div>}

      <p className="sig-analysis">{s.analysis}</p>

      <div className="sig-actions">
        <button className="btn-ghost" onClick={() => onOpenStock(s.ticker)}>View stock →</button>
      </div>
    </article>
  );
}
