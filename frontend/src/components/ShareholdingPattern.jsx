// Shareholding pattern (scraped from screener.in). Stacked composition bar per quarter.
const COLORS = {
  Promoters: "#6d5efc",
  FIIs: "#ff5ca8",
  DIIs: "#34e7e0",
  Government: "#ffc24b",
  Public: "#9aa0c2",
};

function colorFor(label, i) {
  return COLORS[label] || ["#6d5efc", "#ff5ca8", "#34e7e0", "#ffc24b", "#9aa0c2"][i % 5];
}

export default function ShareholdingPattern({ shareholding }) {
  if (!shareholding || !shareholding.available) return null;
  const { quarters, categories } = shareholding;

  return (
    <section className="panel">
      <h2 className="panel-title">Shareholding Pattern</h2>

      <div className="sh-legend">
        {categories.map((c, i) => (
          <span className="sh-legend-item" key={c.label}>
            <span className="sh-dot" style={{ background: colorFor(c.label, i) }} />
            {c.label}
          </span>
        ))}
      </div>

      <div className="sh-bars">
        {quarters.map((q, qi) => (
          <div className="sh-row" key={q}>
            <span className="sh-q">{q}</span>
            <div className="sh-bar">
              {categories.map((c, i) => {
                const val = c.values[qi];
                if (val == null || val <= 0) return null;
                return (
                  <span
                    key={c.label}
                    className="sh-seg"
                    style={{ width: `${val}%`, background: colorFor(c.label, i) }}
                    title={`${c.label}: ${val}%`}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <a className="attribution" href="https://www.screener.in" target="_blank" rel="noreferrer">
        Data via screener.in ↗
      </a>
    </section>
  );
}
