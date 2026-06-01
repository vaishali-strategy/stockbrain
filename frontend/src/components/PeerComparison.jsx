// Peer comparison from screener.in — the stock vs its sector peers on P/E, ROCE, etc.,
// plus where its P/E sits relative to the peer median.

function fmtCr(v) {
  if (v == null) return "—";
  if (v >= 1e5) return "₹" + (v / 1e5).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " L Cr";
  return "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 }) + " Cr";
}
const fmt = (v, suffix = "") => (v == null ? "—" : `${v}${suffix}`);

export default function PeerComparison({ peers }) {
  if (!peers || !peers.available || !peers.peers?.length) return null;

  const { self_pe, median_pe, median_roce } = peers;
  let verdict = null;
  if (self_pe && median_pe) {
    const disc = Math.round((self_pe / median_pe - 1) * 100);
    const dir = disc <= 0 ? "below" : "above";
    verdict = (
      <span className={disc <= 0 ? "pos" : "tone-warn"}>
        {Math.abs(disc)}% {dir} peer median P/E
      </span>
    );
  }

  return (
    <section className="panel">
      <h2 className="panel-title">
        Peer Comparison
        {median_pe && <span className="quality-score">median P/E {median_pe}</span>}
      </h2>
      {verdict && <p className="peer-verdict">This stock trades {verdict} (median ROCE {fmt(median_roce, "%")}).</p>}

      <div className="table-scroll">
        <table className="data-table peer-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>P/E</th>
              <th>ROCE %</th>
              <th>Mkt Cap</th>
              <th>Div Yld</th>
            </tr>
          </thead>
          <tbody>
            {peers.peers.map((p, i) => (
              <tr key={i} className={i === 0 ? "peer-self" : ""}>
                <td>{p.name}{i === 0 && <span className="peer-you">this stock</span>}</td>
                <td>{fmt(p.pe)}</td>
                <td>{fmt(p.roce)}</td>
                <td>{fmtCr(p.market_cap)}</td>
                <td>{fmt(p.dividend_yield, "%")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <a className="attribution" href="https://www.screener.in" target="_blank" rel="noreferrer">
        Peers via screener.in ↗
      </a>
    </section>
  );
}
