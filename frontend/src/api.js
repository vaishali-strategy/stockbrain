// Tiny API client + formatting helpers shared across components.
// All requests go through the Vite /api proxy (see vite.config.js).

// In dev/browser we go through the Vite proxy (/api). Inside the packaged Electron app
// (loaded from file://) there's no proxy, so talk to the local backend directly.
const API = (typeof window !== "undefined" && window.electronAPI?.apiBase) || "/api";

export async function searchTickers(q) {
  const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error("search failed");
  const data = await res.json();
  return data.results || [];
}

export async function getStock(ticker, period = "3mo") {
  const res = await fetch(`${API}/stock/${encodeURIComponent(ticker)}?period=${period}`);
  if (!res.ok) throw new Error("stock fetch failed");
  return res.json();
}

export async function getFundamentals(ticker) {
  const res = await fetch(`${API}/stock/${encodeURIComponent(ticker)}/fundamentals`);
  if (!res.ok) throw new Error("fundamentals fetch failed");
  return res.json();
}

export async function getTechnicals(ticker) {
  const res = await fetch(`${API}/stock/${encodeURIComponent(ticker)}/technicals`);
  if (!res.ok) throw new Error("technicals fetch failed");
  return res.json();
}

export async function getQuality(ticker) {
  const res = await fetch(`${API}/stock/${encodeURIComponent(ticker)}/quality`);
  if (!res.ok) throw new Error("quality fetch failed");
  return res.json();
}

export async function getSignals() {
  const res = await fetch(`${API}/signals`);
  if (!res.ok) throw new Error("signals fetch failed");
  return res.json();
}

export async function refreshSignals() {
  const res = await fetch(`${API}/signals/refresh`, { method: "POST" });
  if (!res.ok) throw new Error("signals refresh failed");
  return res.json();
}

export async function getSignalsStatus() {
  const res = await fetch(`${API}/signals/status`);
  if (!res.ok) throw new Error("signals status failed");
  return res.json();
}

// --- vault / notes / chat ---

export async function getVaultStatus() {
  const res = await fetch(`${API}/vault-status`);
  if (!res.ok) throw new Error("vault status failed");
  return res.json();
}

export async function setVaultConfig(path) {
  const res = await fetch(`${API}/vault/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  return res.json();
}

export async function syncVault() {
  const res = await fetch(`${API}/sync-vault`, { method: "POST" });
  return res.json();
}

export async function saveNote(note) {
  const res = await fetch(`${API}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(note),
  });
  return res.json();
}

export async function getNotes(ticker) {
  const res = await fetch(`${API}/notes/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error("notes fetch failed");
  const data = await res.json();
  return data.notes || [];
}

// Stream a chat reply. Calls onToken(text) for each delta and onDone(finalObj) at the end.
export async function streamChat(body, onToken, onDone) {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop(); // keep the trailing partial frame
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      let json;
      try {
        json = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (json.done) onDone(json);
      else if (json.token) onToken(json.token);
    }
  }
}

export async function getChatConfig() {
  const res = await fetch(`${API}/chat/config`);
  if (!res.ok) throw new Error("chat config failed");
  return res.json();
}

export async function setChatConfig(body) {
  const res = await fetch(`${API}/chat/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

// Analyze the whole portfolio: fundamental good/watch/weak verdict + news impact per holding.
// Holdings are client-side, so we POST them; `force` bypasses the backend's per-ticker cache.
export async function analyzePortfolio(holdings, force = false) {
  const res = await fetch(`${API}/portfolio/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ holdings, force }),
  });
  if (!res.ok) throw new Error("portfolio analyze failed");
  return res.json();
}

export async function getQuote(ticker) {
  const res = await fetch(`${API}/quote/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error("quote fetch failed");
  return res.json();
}

export async function getNews(ticker, limit = 5) {
  const res = await fetch(`${API}/news/${encodeURIComponent(ticker)}?limit=${limit}`);
  if (!res.ok) throw new Error("news fetch failed");
  const data = await res.json();
  return data.news || [];
}

export async function getChart(ticker, period) {
  const res = await fetch(`${API}/chart/${encodeURIComponent(ticker)}?period=${period}`);
  if (!res.ok) throw new Error("chart fetch failed");
  return res.json();
}

// --- formatting (INR-first; never assume USD) ---

export function formatRupees(value) {
  if (value === null || value === undefined) return "—";
  return "₹" + Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

// Indian-style abbreviation: Cr (crore) / L (lakh) for big numbers like market cap.
export function formatLargeRupees(value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (n >= 1e7) return "₹" + (n / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " Cr";
  if (n >= 1e5) return "₹" + (n / 1e5).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " L";
  return formatRupees(n);
}

export function formatNumber(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("en-IN");
}

export function formatPct(value) {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}%`;
}

export function timeAgo(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.max(0, Date.now() - then);
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// NSE trades 09:15–15:30 IST, Mon–Fri. IST = UTC+5:30.
export function isMarketOpen() {
  const now = new Date();
  const utcMins = now.getUTCHours() * 60 + now.getUTCMinutes();
  const istMins = (utcMins + 330) % 1440;
  const istDay = (now.getUTCDay() + (utcMins + 330 >= 1440 ? 1 : 0)) % 7;
  const isWeekday = istDay >= 1 && istDay <= 5;
  return isWeekday && istMins >= 555 && istMins <= 930; // 9:15–15:30 IST
}

export function marketStatus() {
  return isMarketOpen() ? "Market open" : "Market closed";
}

export function nowTimeIST() {
  return new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Asia/Kolkata",
  });
}
