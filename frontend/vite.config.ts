import { defineConfig } from "vite";

// Proxy /api to the FastAPI backend during development so the browser can use
// same-origin requests (no CORS dance).
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
