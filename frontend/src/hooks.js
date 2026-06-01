// Small shared hooks for live polling.
import { useEffect, useRef, useState } from "react";

// True while the tab is visible — used to pause polling in background tabs.
export function useDocumentVisible() {
  const [visible, setVisible] = useState(() => !document.hidden);
  useEffect(() => {
    const h = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", h);
    return () => document.removeEventListener("visibilitychange", h);
  }, []);
  return visible;
}

// Calls `fn` every `delayMs` while `active`. Does not fire immediately (caller
// does the initial fetch). Always uses the latest `fn` without resetting the timer.
export function useInterval(fn, delayMs, active = true) {
  const saved = useRef(fn);
  useEffect(() => {
    saved.current = fn;
  }, [fn]);
  useEffect(() => {
    if (!active || delayMs == null) return;
    const id = setInterval(() => saved.current(), delayMs);
    return () => clearInterval(id);
  }, [delayMs, active]);
}
