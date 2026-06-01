import { useCallback, useEffect, useState } from "react";
import { getQuote, formatRupees, formatPct, isMarketOpen, nowTimeIST } from "../api.js";
import { useWatchlist, removeFromWatchlist } from "../watchlist.js";
import { useDocumentVisible, useInterval } from "../hooks.js";
import Reveal from "./Reveal.jsx";

const POLL_MS = 30000;

export default function Watchlist({ onOpenStock }) {
  const list = useWatchlist();
  const [quotes, setQuotes] = useState({}); // ticker -> quote
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(nowTimeIST());
  const visible = useDocumentVisible();
  const live = isMarketOpen() && visible && list.length > 0;

  const tickers = list.map((i) => i.ticker).join(",");

  // Fetch all quotes. `silent` skips the loading flicker for background polls.
  const fetchQuotes = useCallback(
    async (silent = false) => {
      if (list.length === 0) {
        setQuotes({});
        setLoading(false);
        return;
      }
      if (!silent) setLoading(true);
      const pairs = await Promise.all(
        list.map((i) =>
          getQuote(i.ticker)
            .then((q) => [i.ticker, q])
            .catch(() => [i.ticker, { error: true }])
        )
      );
      setQuotes(Object.fromEntries(pairs));
      setUpdatedAt(nowTimeIST());
      setLoading(false);
    },
    [tickers] // eslint-disable-line react-hooks/exhaustive-deps
  );

  useEffect(() => {
    fetchQuotes(false);
  }, [fetchQuotes]);

  // Live polling while the market is open and the tab is visible.
  useInterval(() => fetchQuotes(true), POLL_MS, live);

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
              {list.length > 0 && (
                <span className="wl-live">
                  {live ? (
                    <> · <span className="live-dot" /> Live · {updatedAt}</>
                  ) : (
                    <> · market closed</>
                  )}
                </span>
              )}
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
