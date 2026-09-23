import { useEffect, useState } from "react";

import FactorsPanel from "../components/FactorsPanel";
import { SampleDataBadge } from "../components/badges";
import { fetchZoneForecasts, fetchZones, generateForecasts, type RiskForecast, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const HORIZONS = [6, 12, 24, 36, 48, 72];

/** PRD §7.9 — 72-hour predictive risk forecast, one card per zone (the
 * prototype's own "per-zone risk grid across six time buckets" screen). */
export default function Forecast() {
  const { token, user } = useAuth();
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [byZone, setByZone] = useState<Record<string, RiskForecast[]>>({});
  const [busyZone, setBusyZone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canWrite = user?.role === "sdma_official";

  const load = () => {
    if (!token) return;
    fetchZones(token)
      .then(async (r) => {
        setZones(r.items);
        const entries = await Promise.all(
          r.items.map(async (z) => [z.zone_id, (await fetchZoneForecasts(token, z.zone_id).catch(() => ({ items: [] }))).items] as const),
        );
        setByZone(Object.fromEntries(entries));
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);

  const generate = async (zoneId: string) => {
    if (!token) return;
    setBusyZone(zoneId);
    setError(null);
    try {
      await generateForecasts(token, zoneId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyZone(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!zones) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading forecasts…</p>;

  return (
    <div style={{ padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 18 }}>72-hour forecast</h2>
        <SampleDataBadge />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {zones.map((z) => {
          const forecasts = byZone[z.zone_id] ?? [];
          const latestByHorizon = new Map<number, RiskForecast>();
          for (const f of forecasts) {
            const existing = latestByHorizon.get(f.horizon_hours);
            if (!existing || f.generated_at > existing.generated_at) latestByHorizon.set(f.horizon_hours, f);
          }
          const peak = [...latestByHorizon.values()].reduce<RiskForecast | null>((max, f) => (!max || f.score > max.score ? f : max), null);

          return (
            <div key={z.zone_id} style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
                <span style={{ font: "600 13px/1.3 var(--font-interface)", color: "var(--ink)" }}>{z.display_code} · {z.name}</span>
                {canWrite && (
                  <button onClick={() => generate(z.zone_id)} disabled={busyZone === z.zone_id} className="ps-btn-primary" style={genButtonStyle}>
                    {busyZone === z.zone_id ? (
                      <>
                        <span className="ps-spinner" /> Generating…
                      </>
                    ) : (
                      "Generate"
                    )}
                  </button>
                )}
              </div>
              <div style={{ padding: 16 }}>
                {latestByHorizon.size === 0 && <p style={{ fontSize: 12, color: "var(--ink3)" }}>No forecast cycle run yet for this zone.</p>}
                {latestByHorizon.size > 0 && (
                  <div key={peak?.generated_at} data-reveal="" style={{ display: "flex", flexDirection: "column" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6 }}>
                      {HORIZONS.map((h) => {
                        const f = latestByHorizon.get(h);
                        const crossing = f && f.score >= 0.65;
                        return (
                          <div
                            key={h}
                            style={{
                              textAlign: "center",
                              padding: "6px 2px",
                              background: "var(--panel2)",
                              border: `1px solid ${crossing ? "var(--sev2)" : "var(--border)"}`,
                              borderRadius: 4,
                            }}
                          >
                            <div style={{ fontSize: 9, color: "var(--ink4)", fontFamily: "var(--font-data)" }}>{h}h</div>
                            <div style={{ fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 13, color: crossing ? "var(--sev2-ink)" : "var(--ink)" }}>
                              {f ? Math.round(f.score * 100) : "—"}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    {peak && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 11, color: "var(--ink3)", marginBottom: 6 }}>
                          Peak value {Math.round(peak.score * 100)} at {peak.horizon_hours}h · model {peak.model_version}
                        </div>
                        <FactorsPanel factors={peak.factors} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const genButtonStyle = {
  background: "var(--accent)",
  color: "var(--on-accent)",
  border: "1px solid var(--accent)",
  borderRadius: 4,
  padding: "5px 11px",
  fontSize: 11,
  fontWeight: 600,
  fontFamily: "var(--font-interface)",
  cursor: "pointer",
} as const;
