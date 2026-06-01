import { useEffect, useState } from "react";
import { saveNote } from "../api.js";

const TYPES = [
  ["company", "Company"],
  ["earnings", "Earnings"],
  ["thesis", "Thesis"],
  ["news", "News"],
  ["journal", "Journal"],
];

// Slide-in panel to write a note into the vault. Keeps the stock data visible behind it.
export default function NoteEditor({ ticker, defaultType = "company", onClose, onSaved, onOpenSettings }) {
  const [noteType, setNoteType] = useState(defaultType);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function save() {
    if (!content.trim() || saving) return;
    setSaving(true);
    setError("");
    const res = await saveNote({ ticker, note_type: noteType, content });
    setSaving(false);
    if (res.error) {
      setError(res.error);
    } else {
      onSaved?.(res);
      onClose();
    }
  }

  const symbol = (ticker || "").replace(/\.(NS|BO)$/, "");

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="note-drawer">
        <div className="drawer-head">
          <h2>Write a note {symbol && <span className="badge">{symbol}</span>}</h2>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>

        <label className="settings-label">Note type</label>
        <div className="note-type-row">
          {TYPES.map(([val, label]) => (
            <button
              key={val}
              className={`filter-pill ${noteType === val ? "active" : ""}`}
              onClick={() => setNoteType(val)}
            >
              {label}
            </button>
          ))}
        </div>

        <label className="settings-label">Note (markdown)</label>
        <textarea
          className="note-textarea"
          placeholder={`Your thoughts on ${symbol || "this stock"}…`}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          autoFocus
        />
        <p className="settings-hint">
          Ticker, type and today's date are added to the frontmatter automatically. Saving indexes
          it instantly for chat.
        </p>

        {error && (
          <div className="drawer-error">
            {error}{" "}
            {onOpenSettings && (
              <button className="link-btn" onClick={onOpenSettings}>Open settings</button>
            )}
          </div>
        )}

        <div className="drawer-actions">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={save} disabled={saving || !content.trim()}>
            {saving ? <span className="spinner" /> : "Save to vault"}
          </button>
        </div>
      </aside>
    </>
  );
}
