import { useEffect, useState } from "react";
import { getVaultStatus, setVaultConfig, syncVault, getChatConfig, setChatConfig } from "../api.js";
import Reveal from "./Reveal.jsx";

export default function ObsidianSync() {
  const [status, setStatus] = useState(null);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [chat, setChat] = useState(null);

  useEffect(() => {
    getChatConfig().then(setChat).catch(() => setChat(null));
  }, []);

  async function saveChat(patch) {
    const next = await setChatConfig(patch);
    setChat(next);
  }

  async function refresh() {
    try {
      const s = await getVaultStatus();
      setStatus(s);
      if (s.vault_path) setPath(s.vault_path);
    } catch {
      setStatus(null);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function save() {
    setBusy(true);
    setMsg("");
    const res = await setVaultConfig(path.trim());
    setBusy(false);
    if (res.ok === false) {
      setMsg(res.error || "Could not set that path.");
    } else {
      setMsg("Saved. Now sync to index your notes.");
      refresh();
    }
  }

  async function sync() {
    setBusy(true);
    setMsg("Indexing your vault…");
    const res = await syncVault();
    setBusy(false);
    if (res.error) setMsg(res.error);
    else {
      setMsg(`Indexed ${res.files_indexed} note(s), ${res.chunks_created} chunk(s).`);
      refresh();
    }
  }

  return (
    <div className="signals-view">
      <Reveal>
        <div className="signals-head">
          <div>
            <h1 className="signals-title">Settings · Vault</h1>
            <p className="signals-sub">Connect an Obsidian vault to chat over your own research.</p>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <section className="panel settings-section">
          <h2 className="panel-title">Obsidian vault</h2>
          <label className="settings-label">Vault folder (absolute path)</label>
          <div className="settings-row">
            <input
              className="searchbar-input"
              placeholder="/Users/you/Documents/MyVault"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
            {window.electronAPI?.selectVaultFolder && (
              <button
                className="btn-ghost"
                onClick={async () => {
                  const picked = await window.electronAPI.selectVaultFolder();
                  if (picked) setPath(picked);
                }}
              >
                Browse…
              </button>
            )}
            <button className="btn-ghost" onClick={save} disabled={busy}>Save</button>
          </div>
          <p className="settings-hint">
            No vault yet? Run <code>npm run seed</code> to generate an example vault, then paste its
            path here.
          </p>

          {status && (
            <div className="vault-stat-grid">
              <Stat label="Status" value={status.vault_configured ? "Connected" : "Not connected"} ok={status.vault_configured} />
              <Stat label="Notes indexed" value={status.total_notes} />
              <Stat label="Chunks" value={status.total_chunks} />
              <Stat label="Last synced" value={status.last_synced ? new Date(status.last_synced).toLocaleString() : "never"} />
            </div>
          )}

          <div className="settings-row">
            <button className="btn-primary" onClick={sync} disabled={busy || !status?.vault_configured}>
              {busy ? <span className="spinner" /> : "↻ Sync vault"}
            </button>
            {msg && <span className="settings-msg">{msg}</span>}
          </div>
        </section>
      </Reveal>

      {chat && (
        <Reveal>
          <section className="panel settings-section">
            <h2 className="panel-title">
              Chat engine
              <span className="quality-score">active: {chat.active}</span>
            </h2>
            <p className="settings-hint" style={{ marginTop: 0 }}>
              {chat.has_key
                ? "Anthropic API key detected."
                : chat.ollama_available
                ? "No API key — using your local Ollama (free, offline)."
                : "No API key and no local Ollama running. Run `ollama run llama3`, or add an Anthropic key, for chat answers."}
            </p>

            <label className="settings-label">Provider</label>
            <div className="note-type-row">
              {[
                ["auto", "Auto"],
                ["anthropic", "Anthropic (Claude)"],
                ["ollama", "Local (Ollama)"],
              ].map(([val, label]) => (
                <button
                  key={val}
                  className={`filter-pill ${chat.provider_setting === val ? "active" : ""}`}
                  onClick={() => saveChat({ provider: val })}
                >
                  {label}
                </button>
              ))}
            </div>

            {(chat.provider_setting === "ollama" ||
              (chat.provider_setting === "auto" && !chat.has_key)) &&
              chat.ollama_models.length > 0 && (
                <>
                  <label className="settings-label">Local model</label>
                  <div className="note-type-row">
                    {chat.ollama_models.map((m) => (
                      <button
                        key={m}
                        className={`filter-pill ${chat.ollama_model === m ? "active" : ""}`}
                        onClick={() => saveChat({ ollama_model: m })}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </>
              )}
          </section>
        </Reveal>
      )}

      <Reveal>
        <section className="panel settings-section">
          <h2 className="panel-title">Privacy</h2>
          <p className="muted">
            StockBrain is local-first: your notes are indexed on your machine with offline
            embeddings, and indexing/search never leave your machine. When you <strong>chat</strong>,
            the relevant note excerpts + live market data are sent to whichever engine you pick above —
            a <strong>local Ollama model stays entirely on your machine</strong>, whereas Anthropic
            (Claude) is a cloud API. Nothing is sent until you ask a question.
          </p>
        </section>
      </Reveal>
    </div>
  );
}

function Stat({ label, value, ok }) {
  return (
    <div className="ratio">
      <div className="ratio-label">{label}</div>
      <div className="ratio-value" style={ok === false ? { color: "var(--text-dim)" } : undefined}>
        {value}
      </div>
    </div>
  );
}
