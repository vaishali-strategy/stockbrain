import { useState } from "react";
import SearchBar from "./components/SearchBar.jsx";
import StockPage from "./components/StockPage.jsx";
import { marketStatus } from "./api.js";

// Simple state machine — no router needed for the slice. home <-> stock.
export default function App() {
  const [view, setView] = useState("home"); // "home" | "stock"
  const [ticker, setTicker] = useState(null);

  function openStock(t) {
    setTicker(t);
    setView("stock");
  }

  function goHome() {
    setView("home");
    setTicker(null);
  }

  return (
    <div className="app">
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
