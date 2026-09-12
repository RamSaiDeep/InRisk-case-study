import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to uvicorn, so the app is same-origin and the
// backend needs no CORS configuration.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
