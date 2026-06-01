import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend lives in frontend/; the backend runs on 8765 this session (8000 was taken on
// this machine). We proxy /api/* to the backend so the app makes same-origin requests and
// CORS/ports stay out of the component code. Override the target with BACKEND_URL.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8765";

export default defineConfig({
  root: "frontend",
  // Relative asset paths so the built app loads from file:// inside Electron.
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: BACKEND_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
