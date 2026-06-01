// Technical analysis panel: synthesized rating, moving averages, oscillators, Bollinger
// Bands, trend strength, key levels (pivots / Fibonacci / support-resistance), volume and
// the latest candlestick pattern. Short descriptions are original explanations of standard
// indicators (the families taught in introductory TA courses such as Zerodha Varsity).

const sigCls = (s) => (s === "bullish" ? "pos" : s === "bearish" ? "neg" : "tone-neutral");
const ratingCls = (label) =>
  label.includes("Buy") ? "rate-buy" : label.includes("Sell") ? "rate-sell" : "rate-neutral";
const fmt = (v) => (v == null ? "—" : v);

export default function TechnicalAnalysis({ tech }) {
  if (!tech || !tech.available) return null;
  const { rating, moving_averages: mas, oscillators, bollinger, trend, volume, levels, candlestick } = tech;
  const lv = levels;

  return (
    <section className="panel tech-panel">
      <h2 className="panel-title">
        Technical Analysis
        <span className="tech-asof">as of {tech.as_of}</span>
      </h2>

      {/* Overall rating */}
      <div className={`tech-rating ${ratingCls(rating.label)}`}>
        <div className="tech-rating-label">{rating.label}</div>
        <div className="tech-rating-counts">
          <span className="pos">{rating.bullish} bullish</span> ·
          <span className="tone-neutral"> {rating.neutral} neutral</span> ·
          <span className="neg"> {rating.bearish} bearish</span>
          <span className="tech-rating-note"> — across {rating.bullish + rating.bearish + rating.neutral} indicators</span>
        </div>
      </div>
      <p className="tech-caveat">
        A mechanical tally of trend + momentum indicators — a starting point, not a recommendation.
      </p>

      <div className="tech-cols">
        {/* Moving averages */}
        <div className="tech-block">
          <h3 className="tech-sub">Moving averages <span className="tech-hint">price vs trend</span></h3>
          <table className="tech-table">
            <tbody>
              {mas.map((m) => (
                <tr key={m.name}>
                  <td>{m.name}</td>
                  <td className="tech-val">₹{m.value}</td>
                  <td className={`tech-sig ${sigCls(m.signal)}`}>{m.signal}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {tech.ma_cross && <div className="tech-note">{tech.ma_cross}</div>}
        </div>

        {/* Oscillators */}
        <div className="tech-block">
          <h3 className="tech-sub">Oscillators <span className="tech-hint">momentum</span></h3>
          <table className="tech-table">
            <tbody>
              {oscillators.map((o) => (
                <tr key={o.name} title={o.note}>
                  <td>{o.name}</td>
                  <td className="tech-val">{fmt(o.value)}</td>
                  <td className={`tech-sig ${sigCls(o.signal)}`}>{o.signal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Volatility + trend strength */}
      <div className="tech-strip">
        {bollinger && (
          <Stat label="Bollinger %B" value={`${bollinger.percent_b}%`}
            sub={`₹${bollinger.lower} – ${bollinger.upper}`} sig={bollinger.signal} />
        )}
        {tech.atr != null && <Stat label="ATR (14)" value={`₹${tech.atr}`} sub="avg true range / volatility" />}
        {trend?.adx != null && (
          <Stat label="ADX (14)" value={trend.adx} sub={`${trend.strength} trend · +DI ${trend.plus_di} / −DI ${trend.minus_di}`} />
        )}
        {volume?.ratio != null && (
          <Stat label="Volume vs 20d" value={`${volume.ratio}×`} sub={`OBV ${volume.obv_trend || "—"}`} />
        )}
      </div>

      {/* Key levels */}
      <div className="tech-block">
        <h3 className="tech-sub">Key levels</h3>
        <div className="tech-52w">
          <div className="tech-52w-bar">
            <div className="tech-52w-fill" style={{ width: `${lv.position_pct ?? 50}%` }} />
          </div>
          <div className="tech-52w-labels">
            <span>52w low ₹{lv.week52_low}</span>
            <span>{lv.position_pct}% of range</span>
            <span>₹{lv.week52_high} high</span>
          </div>
        </div>

        <div className="tech-levels-grid">
          <div className="level-card">
            <div className="level-card-title">Support / Resistance</div>
            <div className="level-row"><span>Resistance</span><span className="neg">₹{lv.resistance}</span></div>
            <div className="level-row"><span>Support</span><span className="pos">₹{lv.support}</span></div>
            <div className="level-card-foot">recent 3-month swing</div>
          </div>

          <div className="level-card">
            <div className="level-card-title">Pivot points</div>
            {["R3", "R2", "R1", "PP", "S1", "S2", "S3"].map((k) => (
              <div key={k} className="level-row">
                <span className={k.startsWith("R") ? "neg" : k.startsWith("S") ? "pos" : ""}>{k}</span>
                <span>₹{lv.pivots[k]}</span>
              </div>
            ))}
          </div>

          {lv.fibonacci?.length > 0 && (
            <div className="level-card">
              <div className="level-card-title">Fibonacci retracement</div>
              {lv.fibonacci.map((f) => (
                <div key={f.level} className="level-row"><span>{f.level}%</span><span>₹{f.price}</span></div>
              ))}
              <div className="level-card-foot">on the 3-month swing</div>
            </div>
          )}
        </div>
      </div>

      {candlestick && (
        <div className="tech-candle">
          <span className="tech-candle-tag">Last candle</span>
          <strong>{candlestick.pattern}</strong> — {candlestick.implication}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value, sub, sig }) {
  return (
    <div className="tech-stat">
      <div className="tech-stat-label">{label}</div>
      <div className={`tech-stat-value ${sig ? sigCls(sig) : ""}`}>{value}</div>
      {sub && <div className="tech-stat-sub">{sub}</div>}
    </div>
  );
}
