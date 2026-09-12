import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// TRD §4: "Field app: React + Vite as a PWA, Workbox service worker,
// IndexedDB via Dexie." vite-plugin-pwa generates the Workbox service
// worker (precaches the app shell so the capture form loads with no
// connectivity at all) — the actual offline QUEUE is Dexie (src/db.ts),
// not the service worker, since a SW can't run arbitrary write logic.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico}"],
      },
      manifest: {
        name: "PS191 Field Survey",
        short_name: "PS191 Field",
        description: "Hazard vulnerability-assessment survey capture — offline-first field app",
        theme_color: "#070b16",
        background_color: "#070b16",
        display: "standalone",
        icons: [],
      },
    }),
  ],
  server: {
    host: true,
    port: 5174,
    watch: {
      // Docker Desktop on Windows doesn't reliably forward native fs-change
      // events into the container (same issue found in the dashboard's
      // vite.config.ts during Phase 3).
      usePolling: true,
    },
  },
});
