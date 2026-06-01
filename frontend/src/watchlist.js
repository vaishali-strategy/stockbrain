// Local, vault-less watchlist persisted in localStorage. Each entry is
// { ticker, name, exchange }. A custom "watchlist-changed" event lets every
// component (nav badge, views) react to changes within the same tab.
import { useEffect, useState } from "react";

const KEY = "stockbrain.watchlist";

export function getWatchlist() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || [];
  } catch {
    return [];
  }
}

function save(list) {
  localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("watchlist-changed"));
}

export function isWatched(ticker) {
  return getWatchlist().some((i) => i.ticker === ticker);
}

export function addToWatchlist(item) {
  const list = getWatchlist();
  if (!list.some((i) => i.ticker === item.ticker)) {
    save([...list, item]);
  }
}

export function removeFromWatchlist(ticker) {
  save(getWatchlist().filter((i) => i.ticker !== ticker));
}

export function toggleWatchlist(item) {
  if (isWatched(item.ticker)) removeFromWatchlist(item.ticker);
  else addToWatchlist(item);
}

// Reactive hook — re-renders on any watchlist change (this tab or another).
export function useWatchlist() {
  const [list, setList] = useState(getWatchlist);
  useEffect(() => {
    const handler = () => setList(getWatchlist());
    window.addEventListener("watchlist-changed", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("watchlist-changed", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);
  return list;
}
