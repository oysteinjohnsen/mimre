import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // FastAPI dev server (port 8000 is taken by another container on this machine).
      "/api": "http://localhost:8010",
    },
  },
});
