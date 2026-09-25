import { useEffect, useState } from "react";

import FactorsPanel from "../components/FactorsPanel";
import { SampleDataBadge } from "../components/badges";
import { fetchZoneForecasts, fetchZones, generateForecasts, type RiskForecast, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { riskColor } from "../lib/riskColor";
import { useTheme } from "../lib/ThemeContext";

const HORIZONS = [6, 12, 24, 36, 48, 72];

// One line per app/ml/forecast_model.py's FEATURE_NAMES — plain-language
// enough for a district official to read at a glance, not a data
// dictionary. Keyed by the exact factor name the backend sends so a
// factor this doesn't recognise just renders without a description
// rather than breaking.
const FACTOR_GLOSSARY: Record<string, string> = {
  susceptibility_score: "How prone this zone's terrain and soil are to landslide/flood risk, from historical GSI geological survey data.",
  rainfall_72h_mm: "Total rainfall forecast over the next 72 hours, in millimetres.",
  slope_degrees: "Steepness of the terrain — steeper slopes raise landslide risk.",
  horizon_hours: "How far ahead this specific data point is projecting (e.g. 24h = the risk level 24 hours from now).",
};

// Same 0-100 breakpoints as lib/riskColor.ts (28/45/65/80), so a zone's
// colour on the Red zone map and its guidance here never disagree — this
// just adds an action to each band riskColor.ts already draws.
const RISK_GUIDANCE_BANDS = [
  { min: 80, label: "Critical", action: "Immediate / emergency relocation — move all households in the zone now." },
  { min: 65, label: "High", action: "Begin phased relocation — start moving the highest-priority households." },
  { min: 45, label: "Moderate", action: "Issue an alert and prepare shelters — stage vehicles and confirm capacity." },
  { min: 28, label: "Low-moderate", action: "Monitor closely — no relocation action needed yet." },
  { min: 0, label: "Low", action: "Routine monitoring only." },
] as const;

function guidanceFor(scorePct: number) {
  return RISK_GUIDANCE_BANDS.find((b) => scorePct >= b.min) ?? RISK_GUIDANCE_BANDS[RISK_GUIDANCE_BANDS.length - 1];
}

/** PRD §7.9 — 72-hour predictive risk forecast, one card per zone (the
 * prototype's own "per-zone risk grid across six time buckets" screen). */
export default function Forecast() {
  const { token, user } = useAuth();
  const { theme } = useTheme();
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
                        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(260px, 1fr)", gap: 16 }}>
                          <FactorsPanel factors={peak.factors} />
                          <ForecastGuidance peak={peak} theme={theme} />
                        </div>
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

/** Plain-language companion to FactorsPanel's raw numbers — what each
 * factor means, what the 0-100 score scale means, and what to actually
 * do about this zone's peak forecast value, for a district official who
 * doesn't want to interpret SHAP contributions by hand. The band
 * breakpoints are lib/riskColor.ts's own (28/45/65/80), so this can never
 * recommend an action the Red zone map's colour for the same score would
 * contradict. */
function ForecastGuidance({ peak, theme }: { peak: RiskForecast; theme: ReturnType<typeof useTheme>["theme"] }) {
  const scorePct = Math.round(peak.score * 100);
  const current = guidanceFor(scorePct);
  const factorNames = peak.factors.map((f) => f.name).filter((name) => name in FACTOR_GLOSSARY);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 11, color: "var(--ink3)" }}>
      <div
        style={{
          padding: "9px 10px",
          borderRadius: 4,
          border: `1px solid ${riskColor(peak.score, theme)}`,
          background: "var(--panel2)",
        }}
      >
        <div style={{ fontFamily: "var(--font-data)", fontSize: 9.5, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 3 }}>
          At {scorePct} · {current.label} — recommended action
        </div>
        <div style={{ fontSize: 12, color: "var(--ink)", fontWeight: 600 }}>{current.action}</div>
      </div>

      {factorNames.length > 0 && (
        <div>
          <div style={{ fontFamily: "var(--font-data)", fontSize: 9.5, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 4 }}>
            What these factors mean
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {factorNames.map((name) => (
              <div key={name}>
                <span style={{ fontFamily: "var(--font-data)", color: "var(--ink2)" }}>{name}</span>
                <span> — {FACTOR_GLOSSARY[name]}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div style={{ fontFamily: "var(--font-data)", fontSize: 9.5, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 4 }}>
          Risk score scale (0-100)
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {RISK_GUIDANCE_BANDS.map((band, i) => {
            const upper = i === 0 ? 100 : RISK_GUIDANCE_BANDS[i - 1].min - 1;
            const range = band.min === upper ? `${band.min}` : `${band.min}-${upper}`;
            return (
              <div key={band.label} style={{ display: "flex", gap: 6, alignItems: "baseline" }}>
                <span
                  style={{
                    flex: "none",
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: riskColor(band.min / 100, theme),
                    alignSelf: "center",
                  }}
                />
                <span style={{ fontFamily: "var(--font-data)", color: "var(--ink4)", minWidth: 44 }}>{range}</span>
                <span style={{ color: "var(--ink3)" }}>
                  <strong style={{ color: "var(--ink2)" }}>{band.label}</strong> — {band.action}
                </span>
              </div>
            );
          })}
        </div>
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
