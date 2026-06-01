"use strict";

// Bridges a minimal, safe API to the renderer. The frontend uses electronAPI.apiBase to
// talk to the local backend directly (no Vite proxy when running as a packaged app), and
// the native folder picker / external-link opener.

const { contextBridge, ipcRenderer } = require("electron");

const port = Number(process.env.BACKEND_PORT) || 8765;

contextBridge.exposeInMainWorld("electronAPI", {
  apiBase: `http://127.0.0.1:${port}`,
  selectVaultFolder: () => ipcRenderer.invoke("select-vault-folder"),
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
  getAppVersion: () => ipcRenderer.invoke("app-version"),
});
