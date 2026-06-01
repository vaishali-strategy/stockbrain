// Local portfolio of holdings, persisted in localStorage. Each holding is
// { ticker, name, qty, avg_price }. Live P&L is computed in the view from live quotes.
// A "portfolio-changed" event keeps every component in sync within the tab.
import { useEffect, useState } from "react";

const KEY = "stockbrain.portfolio";

export function getHoldings() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || [];
  } catch {
    return [];
  }
}

function save(list) {
  localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("portfolio-changed"));
}

// Normalize a broker symbol to a Yahoo ticker: strip series suffixes, default to NSE (.NS).
export function normalizeTicker(symbol) {
  let s = (symbol || "").trim().toUpperCase();
  if (!s) return "";
  s = s.replace(/-(EQ|BE|BZ|SM|ST)$/i, ""); // common NSE series suffixes
  if (s.endsWith(".NS") || s.endsWith(".BO")) return s;
  return `${s}.NS`;
}

export function addHolding({ ticker, name, qty, avg_price }) {
  const t = normalizeTicker(ticker);
  if (!t || !(qty > 0)) return;
  const list = getHoldings();
  const i = list.findIndex((h) => h.ticker === t);
  if (i >= 0) {
    // Merge into the existing position with a weighted-average buy price.
    const ex = list[i];
    const totQty = ex.qty + qty;
    const avg = totQty ? (ex.qty * ex.avg_price + qty * avg_price) / totQty : avg_price;
    list[i] = { ...ex, qty: totQty, avg_price: round2(avg), name: ex.name || name };
  } else {
    list.push({ ticker: t, name: name || t.replace(/\.(NS|BO)$/, ""), qty, avg_price: round2(avg_price) });
  }
  save(list);
}

export function updateHolding(ticker, patch) {
  const list = getHoldings();
  const i = list.findIndex((h) => h.ticker === ticker);
  if (i >= 0) {
    list[i] = { ...list[i], ...patch };
    save(list);
  }
}

export function removeHolding(ticker) {
  save(getHoldings().filter((h) => h.ticker !== ticker));
}

export function clearHoldings() {
  save([]);
}

export function usePortfolio() {
  const [list, setList] = useState(getHoldings);
  useEffect(() => {
    const handler = () => setList(getHoldings());
    window.addEventListener("portfolio-changed", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("portfolio-changed", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);
  return list;
}

const round2 = (v) => Math.round(Number(v) * 100) / 100;

// --- CSV import (generic; calibrated to a real broker export later) ---

function splitCsvLine(line) {
  const out = [];
  let cur = "";
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') inQ = !inQ;
    else if (ch === "," && !inQ) {
      out.push(cur);
      cur = "";
    } else cur += ch;
  }
  out.push(cur);
  return out.map((s) => s.trim().replace(/^"|"$/g, ""));
}

function findCol(headers, includes, excludes = []) {
  for (let i = 0; i < headers.length; i++) {
    const h = headers[i].toLowerCase();
    if (includes.some((n) => h.includes(n)) && !excludes.some((n) => h.includes(n))) return i;
  }
  return -1;
}

// Returns { holdings: [{ticker,name,qty,avg_price}], skipped, error }.
export function parseHoldingsCSV(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return { holdings: [], skipped: 0, error: "CSV looks empty." };

  // Find the header row (first row that mentions a quantity-like column).
  let headerIdx = lines.findIndex((l) => /qty|quantity|shares/i.test(l));
  if (headerIdx < 0) headerIdx = 0;
  const headers = splitCsvLine(lines[headerIdx]);

  const iSym = findCol(headers, ["symbol", "tradingsymbol", "ticker", "instrument", "stock", "scrip"]);
  const iQty = findCol(headers, ["qty", "quantity", "shares"]);
  const iAvg = findCol(headers, ["avg", "average", "buy price", "buy avg", "cost", "purchase"], ["ltp", "last", "current", "market", "close"]);
  if (iSym < 0 || iQty < 0 || iAvg < 0) {
    return { holdings: [], skipped: 0, error: "Couldn't find Symbol / Quantity / Avg-price columns in this CSV." };
  }

  const holdings = [];
  let skipped = 0;
  for (let r = headerIdx + 1; r < lines.length; r++) {
    const cells = splitCsvLine(lines[r]);
    const sym = cells[iSym];
    const qty = parseFloat((cells[iQty] || "").replace(/[^0-9.\-]/g, ""));
    const avg = parseFloat((cells[iAvg] || "").replace(/[^0-9.\-]/g, ""));
    if (!sym || !(qty > 0) || !(avg > 0)) {
      skipped++;
      continue;
    }
    holdings.push({ ticker: normalizeTicker(sym), name: sym, qty, avg_price: round2(avg) });
  }
  return { holdings, skipped, error: holdings.length ? null : "No valid holdings rows found." };
}
