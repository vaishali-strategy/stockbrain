import { useEffect, useState } from "react";
import { getNews, timeAgo } from "../api.js";
import { useDocumentVisible, useInterval } from "../hooks.js";

const POLL_MS = 180000; // re-pull headlines every 3 minutes while visible

export default function NewsFeed({ ticker, news: initial }) {
  const [news, setNews] = useState(initial || []);
  const visible = useDocumentVisible();

  useEffect(() => {
    setNews(initial || []);
  }, [ticker, initial]);

  // News breaks at any hour, so refresh regardless of market hours (just when visible).
  useInterval(
    async () => {
      try {
        const fresh = await getNews(ticker, 5);
        if (fresh.length) setNews(fresh);
      } catch {
        /* keep current */
      }
    },
    POLL_MS,
    visible && !!ticker
  );

  if (!news || news.length === 0) {
    return (
      <section className="panel">
        <h2 className="panel-title">News</h2>
        <p className="muted">No recent news found.</p>
      </section>
    );
  }

  // In Electron we open links in the system browser; in the browser, a normal new tab.
  function open(url) {
    if (window.electronAPI?.openExternal) window.electronAPI.openExternal(url);
    else window.open(url, "_blank", "noopener");
  }

  return (
    <section className="panel">
      <h2 className="panel-title">News</h2>
      <ul className="news-list">
        {news.map((item, i) => (
          <li key={item.url || i} className="news-item" onClick={() => open(item.url)}>
            <div className="news-title">{item.title}</div>
            <div className="news-meta">
              <span>{item.source || "Unknown"}</span>
              {item.published_at && <span>· {timeAgo(item.published_at)}</span>}
              <span className="news-ext">↗</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
