"use strict";

// Electron main process: launches the Python backend, waits for it to be healthy, then
// opens the app window. In dev (unpackaged) the backend is run from the project venv; a
// frozen PyInstaller sidecar for packaged builds is a later step.

const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");

const BACKEND_PORT = Number(process.env.BACKEND_PORT) || 8765;
const ROOT = path.join(__dirname, "..");

let backendProc = null;
let mainWindow = null;

// ---------------------------------------------------------------- backend lifecycle
function healthCheck() {
  return new Promise((resolve) => {
    const req = http.get({ host: "127.0.0.1", port: BACKEND_PORT, path: "/health", timeout: 1000 }, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

async function waitForBackend(timeoutMs = 40000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await healthCheck()) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function startBackend() {
  // Prefer the project virtualenv's Python; fall back to a frozen sidecar when packaged.
  const venvPy = process.platform === "win32"
    ? path.join(ROOT, ".venv", "Scripts", "python.exe")
    : path.join(ROOT, ".venv", "bin", "python");
  const sidecar = path.join(process.resourcesPath || ROOT, "stockbrain-server");

  let cmd, args;
  if (app.isPackaged && require("fs").existsSync(sidecar)) {
    cmd = sidecar;
    args = ["--port", String(BACKEND_PORT)];
  } else {
    cmd = venvPy;
    args = ["-m", "uvicorn", "backend.main:app", "--port", String(BACKEND_PORT)];
  }

  backendProc = spawn(cmd, args, { cwd: ROOT, stdio: "inherit", env: { ...process.env, BACKEND_PORT: String(BACKEND_PORT) } });
  backendProc.on("error", (err) => console.error("[backend] failed to start:", err));
  backendProc.on("exit", (code) => console.log("[backend] exited", code));
}

function stopBackend() {
  if (backendProc && !backendProc.killed) {
    backendProc.kill();
    backendProc = null;
  }
}

// ---------------------------------------------------------------- window
const LOADING_HTML =
  "data:text/html," +
  encodeURIComponent(`<!doctype html><html><body style="margin:0;height:100vh;display:flex;
  align-items:center;justify-content:center;background:#07060f;color:#a39fc4;
  font-family:-apple-system,sans-serif"><div style="text-align:center">
  <div style="font-size:22px;font-weight:700;background:linear-gradient(135deg,#6d5efc,#ff5ca8);
  -webkit-background-clip:text;color:transparent">StockBrain</div>
  <div style="margin-top:10px;font-size:13px">Starting up…</div></div></body></html>`);

function appIndex() {
  return path.join(ROOT, "frontend", "dist", "index.html");
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: "#07060f",
    title: "StockBrain",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Open external links (target=_blank, website/news links) in the system browser.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.loadURL(LOADING_HTML);
  const ok = await waitForBackend();
  if (!ok) {
    await mainWindow.loadURL(
      "data:text/html," +
        encodeURIComponent(`<body style="background:#07060f;color:#ff6b8b;font-family:sans-serif;
        padding:40px">Backend didn't start. Check that Python deps are installed
        (<code>bash scripts/setup.sh</code>).</body>`)
    );
    return;
  }

  const devUrl = process.env.VITE_DEV_SERVER;
  if (devUrl) await mainWindow.loadURL(devUrl);
  else await mainWindow.loadFile(appIndex());

  mainWindow.on("closed", () => (mainWindow = null));
}

// ---------------------------------------------------------------- app lifecycle
app.whenReady().then(async () => {
  if (!(await healthCheck())) startBackend(); // reuse a backend already running in dev
  await createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("quit", stopBackend);

// ---------------------------------------------------------------- IPC
ipcMain.handle("select-vault-folder", async () => {
  const res = await dialog.showOpenDialog(mainWindow, {
    title: "Select your Obsidian vault",
    properties: ["openDirectory"],
  });
  return res.canceled || !res.filePaths.length ? null : res.filePaths[0];
});

ipcMain.handle("open-external", (_e, url) => {
  if (/^https?:/.test(url)) shell.openExternal(url);
});

ipcMain.handle("app-version", () => app.getVersion());
