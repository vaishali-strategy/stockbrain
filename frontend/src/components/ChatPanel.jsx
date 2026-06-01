import { useEffect, useRef, useState } from "react";
import { streamChat, getVaultStatus } from "../api.js";

export default function ChatPanel({ initialTicker = null, onOpenSettings }) {
  const [messages, setMessages] = useState([]); // {role, content, sources?}
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [vault, setVault] = useState(null);
  const inputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    getVaultStatus().then(setVault).catch(() => setVault(null));
  }, []);

  // Cmd/Ctrl+K focuses the input.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", sources: [], streaming: true },
    ]);

    const appendToLast = (fn) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = fn(next[next.length - 1]);
        return next;
      });

    try {
      await streamChat(
        { message: text, ticker_context: initialTicker, conversation_history: history },
        (token) => appendToLast((m) => ({ ...m, content: m.content + token })),
        (final) =>
          appendToLast((m) => ({
            ...m,
            sources: final.sources || [],
            ai_generated: final.ai_generated,
            provider: final.provider,
            streaming: false,
          }))
      );
    } catch {
      appendToLast((m) => ({ ...m, content: m.content + "\n\n[Connection error]", streaming: false }));
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  const vaultless = vault && (!vault.vault_configured || vault.total_chunks === 0);

  return (
    <div className="chat-panel signals-view">
      <div className="signals-head">
        <div>
          <h1 className="signals-title">Chat</h1>
          <p className="signals-sub">
            Ask about any stock {initialTicker ? `(context: ${initialTicker.replace(/\.(NS|BO)$/, "")})` : ""} —
            answers blend live market data with your vault notes.
          </p>
        </div>
      </div>

      {vaultless && (
        <div className="chat-banner">
          You're in <strong>data mode</strong> — answers use live market data + AI knowledge.{" "}
          <button className="link-btn" onClick={onOpenSettings}>Connect your Obsidian vault</button>{" "}
          to include your personal research.
        </div>
      )}

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty muted">
            Try: “What's my thesis on HDFC Bank?” · “Summarise TCS's last quarter” ·
            “How does Reliance look right now?”
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="chat-bubble">
              {m.content || (m.streaming ? <span className="typing">●●●</span> : "")}
              {m.role === "assistant" && !m.streaming && m.provider && (
                <div className="chat-engine">answered by {m.provider}</div>
              )}
              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div className="chat-sources">
                  <span className="chat-sources-label">Sources</span>
                  {m.sources.map((s, j) => (
                    <span key={j} className="source-chip">
                      📄 {s.filename}
                      {s.ticker ? ` · ${s.ticker}` : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Ask anything…  (⌘K to focus, Enter to send)"
          value={input}
          rows={1}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="btn-primary" onClick={send} disabled={sending || !input.trim()}>
          {sending ? <span className="spinner" /> : "Send"}
        </button>
      </div>
    </div>
  );
}
