import { useEffect, useState } from "react";

import ZoneMap from "./components/ZoneMap";
import { fetchZones, login, type Zone } from "./lib/api";

/**
 * Dev-only integration harness for Phase 3 — proves the real Leaflet/API
 * wiring works end to end. Not the real dashboard: there's no login screen,
 * role switching, or layout shell yet (all Phase 8). The hardcoded seeded
 * credentials below get replaced by the real login flow when Phase 8 lands.
 */
const DEV_EMAIL = "sdma.official@ps191.dev";
const DEV_PASSWORD = "ps191-demo-pass";

export default function App() {
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await login(DEV_EMAIL, DEV_PASSWORD);
        const response = await fetchZones(token);
        if (!cancelled) setZones(response.items);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", height: "100vh", display: "flex", flexDirection: "column" }}>
      <h1 style={{ padding: "0.75rem 1rem", margin: 0, fontSize: "1rem" }}>
        PS191 — Hazard Red-Zone &amp; Relocation Platform
      </h1>
      <p style={{ padding: "0 1rem", margin: "0 0 0.5rem", fontSize: "0.8rem", opacity: 0.7 }}>
        Dev harness for the Phase 3 zone map — the real dashboard shell lands in Phase 8.
      </p>
      <div style={{ flex: 1, position: "relative" }}>
        {error && <p style={{ padding: "1rem", color: "#B80C09" }}>Failed to load zones: {error}</p>}
        {!error && zones && <ZoneMap zones={zones} />}
        {!error && !zones && <p style={{ padding: "1rem" }}>Loading zones…</p>}
      </div>
    </main>
  );
}
