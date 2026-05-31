import { timeAgo } from "../api.js";

export default function NewsFeed({ news }) {
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
          <li key={i} className="news-item" onClick={() => open(item.url)}>
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
