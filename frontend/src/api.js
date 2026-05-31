// Tiny API client + formatting helpers shared across components.
// All requests go through the Vite /api proxy (see vite.config.js).

const API = "/api";

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

export async function getQuote(ticker) {
  const res = await fetch(`${API}/quote/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error("quote fetch failed");
  return res.json();
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
export function marketStatus() {
  const now = new Date();
  const utcMins = now.getUTCHours() * 60 + now.getUTCMinutes();
  const istMins = (utcMins + 330) % 1440;
  const istDay = (now.getUTCDay() + (utcMins + 330 >= 1440 ? 1 : 0)) % 7;
  const isWeekday = istDay >= 1 && istDay <= 5;
  const open = isWeekday && istMins >= 555 && istMins <= 930; // 9:15–15:30
  return open ? "Market open" : "Market closed";
}
