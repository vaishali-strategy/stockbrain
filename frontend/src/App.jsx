import { useEffect, useState } from "react";
import SearchBar from "./components/SearchBar.jsx";
import StockPage from "./components/StockPage.jsx";
import { marketStatus } from "./api.js";

// Simple state machine — no router needed for the slice. home <-> stock.
function tickerFromHash() {
  const h = decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();
  return h || null;
}

export default function App() {
  // Initialize from the URL hash so stock pages are bookmarkable/shareable.
  const initial = tickerFromHash();
  const [view, setView] = useState(initial ? "stock" : "home");
  const [ticker, setTicker] = useState(initial);

  // Keep state in sync with back/forward navigation.
  useEffect(() => {
    function onHash() {
      const t = tickerFromHash();
      setTicker(t);
      setView(t ? "stock" : "home");
    }
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Parallax: drift the aurora as the page scrolls (rAF-throttled).
  useEffect(() => {
    let raf = 0;
    function onScroll() {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        const y = window.scrollY || 0;
        document.documentElement.style.setProperty("--par", `${y * 0.18}px`);
        raf = 0;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function openStock(t) {
    setTicker(t);
    setView("stock");
    window.location.hash = encodeURIComponent(t);
    window.scrollTo({ top: 0 });
  }

  function goHome() {
    setView("home");
    setTicker(null);
    window.location.hash = "";
  }

  return (
    <div className="app">
      <div className="aurora" aria-hidden="true">
        <span className="a1" />
        <span className="a2" />
      </div>

      <header className="topbar">
        <button className="brand" onClick={goHome}>StockBrain</button>
        <span className="market-status">{marketStatus()}</span>
      </header>

      {view === "home" && (
        <main className="home">
          <h1 className="home-title">Search any stock</h1>
          <p className="home-sub">Live NSE/BSE prices, charts, financials, news — no setup needed.</p>
          <SearchBar onSelect={openStock} autoFocus large />
        </main>
      )}

      {view === "stock" && ticker && (
        <main className="stock-view">
          <div className="stock-search-row">
            <SearchBar onSelect={openStock} />
          </div>
          <StockPage ticker={ticker} />
        </main>
      )}
    </div>
  );
}
