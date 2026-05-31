import { useEffect, useRef, useState } from "react";
import { searchTickers } from "../api.js";

const RECENT_KEY = "stockbrain.recentSearches";

function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY)) || [];
  } catch {
    return [];
  }
}

function saveRecent(item) {
  const recent = loadRecent().filter((r) => r.ticker !== item.ticker);
  recent.unshift(item);
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 8)));
}

export default function SearchBar({ onSelect, autoFocus = false, large = false }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef(null);

  // Debounced search (300ms).
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      return;
    }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        setResults(await searchTickers(q));
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  // Close dropdown on outside click.
  useEffect(() => {
    function onClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function choose(item) {
    saveRecent(item);
    setQuery("");
    setResults([]);
    setOpen(false);
    onSelect(item.ticker);
  }

  function onKeyDown(e) {
    if (e.key === "Enter") {
      if (results.length > 0) choose(results[0]);
      else if (query.trim()) onSelect(query.trim().toUpperCase()); // direct ticker entry
    }
    if (e.key === "Escape") setOpen(false);
  }

  const recent = loadRecent();
  const showRecent = focused && !query.trim() && recent.length > 0;

  return (
    <div className={`searchbar ${large ? "searchbar-large" : ""}`} ref={boxRef}>
      <input
        type="text"
        className="searchbar-input"
        placeholder="Search a stock — e.g. Reliance, TCS, HDFC Bank"
        value={query}
        autoFocus={autoFocus}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          setFocused(true);
          if (results.length) setOpen(true);
        }}
        onBlur={() => setTimeout(() => setFocused(false), 150)}
        onKeyDown={onKeyDown}
      />

      {open && (query.trim() || loading) && (
        <ul className="search-dropdown">
          {loading && <li className="search-empty">Searching…</li>}
          {!loading && results.length === 0 && <li className="search-empty">No matches</li>}
          {results.map((r) => (
            <li key={r.ticker} className="search-item" onMouseDown={() => choose(r)}>
              <div className="search-item-main">
                <span className="search-name">{r.name}</span>
                {r.exchange && <span className="badge">{r.exchange}</span>}
              </div>
              {r.sector && <span className="search-sector">{r.sector}</span>}
            </li>
          ))}
        </ul>
      )}

      {showRecent && (
        <ul className="search-dropdown">
          <li className="search-heading">Recent</li>
          {recent.map((r) => (
            <li key={r.ticker} className="search-item" onMouseDown={() => choose(r)}>
              <div className="search-item-main">
                <span className="search-name">{r.name}</span>
                {r.exchange && <span className="badge">{r.exchange}</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
