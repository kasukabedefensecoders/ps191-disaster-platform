import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Docker Desktop on Windows doesn't reliably forward native filesystem
    // change events into the container, so Vite's watcher silently misses
    // host-side edits without polling — confirmed by a stale HMR module
    // surviving a source edit during Phase 3's browser testing.
    watch: {
      usePolling: true,
    },
  },
});
