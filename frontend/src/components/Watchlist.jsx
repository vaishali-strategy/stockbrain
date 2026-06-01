import { useEffect, useState } from "react";
import { getQuote, formatRupees, formatPct } from "../api.js";
import { useWatchlist, removeFromWatchlist } from "../watchlist.js";
import Reveal from "./Reveal.jsx";

export default function Watchlist({ onOpenStock }) {
  const list = useWatchlist();
  const [quotes, setQuotes] = useState({}); // ticker -> quote
  const [loading, setLoading] = useState(true);

  // (Re)fetch quotes whenever the set of tickers changes.
  const tickers = list.map((i) => i.ticker).join(",");
  useEffect(() => {
    let cancelled = false;
    if (list.length === 0) {
      setLoading(false);
      setQuotes({});
      return;
    }
    setLoading(true);
    Promise.all(
      list.map((i) =>
        getQuote(i.ticker)
          .then((q) => [i.ticker, q])
          .catch(() => [i.ticker, { error: true }])
      )
    ).then((pairs) => {
      if (!cancelled) {
        setQuotes(Object.fromEntries(pairs));
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [tickers]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="signals-view">
      <Reveal>
        <div className="signals-head">
          <div>
            <h1 className="signals-title">Watchlist</h1>
            <p className="signals-sub">
              {list.length > 0
                ? `${list.length} stock${list.length > 1 ? "s" : ""} you're tracking`
                : "Stocks you add will show here with live prices."}
            </p>
          </div>
        </div>
      </Reveal>

      {list.length === 0 ? (
        <Reveal>
          <div className="signals-empty panel">
            <h2>Your watchlist is empty</h2>
            <p className="muted">
              Open any stock and tap <strong>☆ Watchlist</strong> to start tracking it here.
            </p>
          </div>
        </Reveal>
      ) : (
        <Reveal>
          <section className="panel watchlist-panel">
            <table className="watchlist-table">
              <tbody>
                {list.map((item) => {
                  const q = quotes[item.ticker];
                  const symbol = item.ticker.replace(/\.(NS|BO)$/, "");
                  const up = q && !q.error && (q.change_pct ?? 0) >= 0;
                  return (
                    <tr key={item.ticker} onClick={() => onOpenStock(item.ticker)}>
                      <td className="wl-id">
                        <span className="search-symbol">{symbol}</span>
                        {item.exchange && <span className="sig-exch">{item.exchange}</span>}
                      </td>
                      <td className="wl-name">{item.name || symbol}</td>
                      <td className="wl-price">
                        {loading || !q ? "…" : q.error ? "—" : formatRupees(q.price)}
                      </td>
                      <td className={`wl-change ${up ? "pos" : "neg"}`}>
                        {q && !q.error && q.change_pct != null ? formatPct(q.change_pct) : ""}
                      </td>
                      <td className="wl-remove">
                        <button
                          title="Remove from watchlist"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeFromWatchlist(item.ticker);
                          }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </Reveal>
      )}
    </div>
  );
}
