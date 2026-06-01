import { useEffect, useState } from "react";
import SearchBar from "./components/SearchBar.jsx";
import StockPage from "./components/StockPage.jsx";
import SignalsDashboard from "./components/SignalsDashboard.jsx";
import Watchlist from "./components/Watchlist.jsx";
import { marketStatus } from "./api.js";
import { useWatchlist } from "./watchlist.js";

// Resolve the current view from the URL hash so views are bookmarkable.
//   #signals        -> signals dashboard
//   #<TICKER>       -> stock page
//   (empty)         -> home
function routeFromHash() {
  const h = decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();
  if (!h) return { view: "home", ticker: null };
  if (h.toLowerCase() === "signals") return { view: "signals", ticker: null };
  if (h.toLowerCase() === "watchlist") return { view: "watchlist", ticker: null };
  return { view: "stock", ticker: h };
}

export default function App() {
  const [{ view, ticker }, setRoute] = useState(routeFromHash);
  const watchlist = useWatchlist();

  // Sync with back/forward + manual hash edits.
  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Parallax: drift the aurora as the page scrolls (rAF-throttled).
  useEffect(() => {
    let raf = 0;
    function onScroll() {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        document.documentElement.style.setProperty("--par", `${(window.scrollY || 0) * 0.18}px`);
        raf = 0;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function go(hash) {
    window.location.hash = hash;
    window.scrollTo({ top: 0 });
    setRoute(routeFromHash()); // immediate update (hashchange also fires)
  }

  const openStock = (t) => go(encodeURIComponent(t));
  const openSignals = () => go("signals");
  const openWatchlist = () => go("watchlist");
  const goHome = () => go("");

  return (
    <div className="app">
      <div className="aurora" aria-hidden="true">
        <span className="a1" />
        <span className="a2" />
      </div>

      <header className="topbar">
        <button className="brand" onClick={goHome}>StockBrain</button>
        <nav className="topnav">
          <button className={view === "signals" ? "navlink active" : "navlink"} onClick={openSignals}>
            AI Signals
          </button>
          <button className={view === "watchlist" ? "navlink active" : "navlink"} onClick={openWatchlist}>
            Watchlist
            {watchlist.length > 0 && <span className="nav-badge">{watchlist.length}</span>}
          </button>
          <span className="market-status">{marketStatus()}</span>
        </nav>
      </header>

      {view === "home" && (
        <main className="home">
          <h1 className="home-title">Search any stock</h1>
          <p className="home-sub">Live NSE/BSE prices, charts, financials, news — no setup needed.</p>
          <SearchBar onSelect={openStock} autoFocus large />
          <button className="home-signals-link" onClick={openSignals}>
            ✨ Explore AI buy/sell signals →
          </button>
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

      {view === "signals" && (
        <main className="stock-view">
          <SignalsDashboard onOpenStock={openStock} />
        </main>
      )}

      {view === "watchlist" && (
        <main className="stock-view">
          <Watchlist onOpenStock={openStock} />
        </main>
      )}
    </div>
  );
}
