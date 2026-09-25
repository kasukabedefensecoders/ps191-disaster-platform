import { useEffect, useState } from "react";

import BeforeAfterSlider from "../components/BeforeAfterSlider";
import { SampleDataBadge } from "../components/badges";
import {
  fetchZoneChangeDetectionImage,
  fetchZoneChangeDetections,
  fetchZoneHouseholds,
  fetchZones,
  fetchSurveys,
  runChangeDetection,
  type ChangeDetection as ChangeDetectionType,
  type HouseholdRanked,
  type Survey,
  type Zone,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";

// app/cv/change_detection.py: PIXEL_SIZE_DEG=0.0001 at this latitude is
// documented there as ~11m/px; IMAGE_SIZE is 200x200px. Used only to turn
// a fraction-of-frame confidence into a human hectare figure — not a
// re-derivation of the backend's geometry, just its own stated scale.
const METRES_PER_PIXEL = 11;
const IMAGE_SIDE_PX = 200;
const FRAME_AREA_HA = (IMAGE_SIDE_PX * METRES_PER_PIXEL * IMAGE_SIDE_PX * METRES_PER_PIXEL) / 10_000;

interface ZoneImages {
  before: string | null;
  after: string | null;
}

/** PRD §7.11 — satellite/SAR rapid damage detection. Ported from
 * PROTOTYPE/PS191 Platform.dc.html's SAR screen (before/after swipe
 * comparison + detection-result panel), but wired to this build's real
 * pipeline: the actual curated synthetic pair (not a stock Sentinel-1
 * photo), the actual OpenCV-detected confidence, and the actual
 * cross-referenced household/survey rows rather than illustrative ones. */
export default function ChangeDetection() {
  const { token, user } = useAuth();
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [byZone, setByZone] = useState<Record<string, ChangeDetectionType[]>>({});
  const [images, setImages] = useState<Record<string, ZoneImages>>({});
  const [households, setHouseholds] = useState<Record<string, HouseholdRanked[]>>({});
  const [surveys, setSurveys] = useState<Survey[] | null>(null);
  const [busyZone, setBusyZone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canWrite = user?.role === "sdma_official";

  const load = () => {
    if (!token) return;
    fetchZones(token)
      .then(async (r) => {
        setZones(r.items);
        const detectionEntries = await Promise.all(
          r.items.map(async (z) => [z.zone_id, (await fetchZoneChangeDetections(token, z.zone_id).catch(() => ({ items: [] }))).items] as const),
        );
        const byZoneMap = Object.fromEntries(detectionEntries);
        setByZone(byZoneMap);

        // Only fetch imagery for a zone once it has an actual detection run
        // recorded — a zone nobody has clicked "Run detection" for this
        // demo cycle shouldn't have its before/after pair loaded, let alone
        // shown, even though the curated pair already exists server-side.
        const zonesWithDetections = r.items.filter((z) => (byZoneMap[z.zone_id] ?? []).length > 0);
        const imageEntries = await Promise.all(
          zonesWithDetections.map(async (z) => {
            const [before, after] = await Promise.all([
              fetchZoneChangeDetectionImage(token, z.zone_id, "before").catch(() => null),
              fetchZoneChangeDetectionImage(token, z.zone_id, "after").catch(() => null),
            ]);
            return [z.zone_id, { before, after }] as const;
          }),
        );
        setImages(Object.fromEntries(imageEntries));

        const householdEntries = await Promise.all(
          r.items.map((z) => fetchZoneHouseholds(token, z.zone_id).then((res) => [z.zone_id, res.items] as const).catch(() => [z.zone_id, []] as const)),
        );
        setHouseholds(Object.fromEntries(householdEntries));
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    fetchSurveys(token)
      .then((r) => setSurveys(r.items))
      .catch(() => {});
  };

  useEffect(load, [token]);

  // Blob URLs are per-fetch — release them when replaced or on unmount so
  // repeated visits to this screen don't leak memory.
  useEffect(() => {
    return () => {
      Object.values(images).forEach((pair) => {
        if (pair.before) URL.revokeObjectURL(pair.before);
        if (pair.after) URL.revokeObjectURL(pair.after);
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [images]);

  const run = async (zoneId: string) => {
    if (!token) return;
    setBusyZone(zoneId);
    setError(null);
    try {
      await runChangeDetection(token, zoneId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyZone(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!zones) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading change detections…</p>;

  return (
    <div style={{ padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 18 }}>SAR change detection</h2>
        <SampleDataBadge />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {zones.map((z) => {
          const detections = byZone[z.zone_id] ?? [];
          const latest = detections[0];
          const zoneHouseholds = households[z.zone_id] ?? [];

          if (!latest) {
            return (
              <div
                key={z.zone_id}
                style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", padding: "12px 14px" }}
              >
                <span style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>
                  {z.display_code} · {z.name}
                </span>
                <span style={{ fontSize: 12, color: "var(--ink3)" }}>Not run yet this demo cycle.</span>
                <div style={{ flex: 1 }} />
                {canWrite && (
                  <button onClick={() => run(z.zone_id)} disabled={busyZone === z.zone_id} className="ps-btn-primary" style={runButtonStyle}>
                    {busyZone === z.zone_id ? "Running…" : "Run detection"}
                  </button>
                )}
              </div>
            );
          }

          const zoneImages = images[z.zone_id];
          const hasImagery = !!(zoneImages?.before && zoneImages?.after);

          return (
            <div key={z.zone_id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.5fr) minmax(280px, 1fr)", gap: 12, alignItems: "start" }}>
              <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden", minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>
                    {z.display_code} · {z.name}
                  </span>
                  <div style={{ flex: 1 }} />
                  {canWrite && (
                    <button onClick={() => run(z.zone_id)} disabled={busyZone === z.zone_id} className="ps-btn-primary" style={runButtonStyle}>
                      {busyZone === z.zone_id ? "Running…" : "Run detection"}
                    </button>
                  )}
                </div>
                {hasImagery ? (
                  <BeforeAfterSlider beforeSrc={zoneImages!.before!} afterSrc={zoneImages!.after!} />
                ) : (
                  <p style={{ padding: 16, fontSize: 12, color: "var(--ink3)" }}>
                    No curated before/after imagery uploaded for this zone yet.
                  </p>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
                <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
                  <div style={{ padding: "12px 15px", borderBottom: "1px solid var(--border)", font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>
                    Detection result
                  </div>
                  <div style={{ padding: "14px 15px", borderBottom: "1px solid var(--border-soft)", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                    <Stat label="Affected area" value={`${(FRAME_AREA_HA * (latest.confidence ?? 0)).toFixed(1)} ha`} />
                    <Stat label="Detected" value={new Date(latest.detected_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} />
                  </div>
                  <div style={{ padding: "14px 15px" }}>
                    <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 10 }}>
                      Cross-referenced against surveys
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                      {latest.cross_referenced_household_ids.length === 0 && latest.cross_referenced_survey_ids.length === 0 && (
                        <p style={{ fontSize: 12, color: "var(--ink3)", margin: 0 }}>No households or surveys fall inside the detected polygon.</p>
                      )}
                      {latest.cross_referenced_household_ids.map((id) => {
                        const h = zoneHouseholds.find((hh) => hh.household_id === id);
                        return (
                          <div key={id} style={xrefRowStyle("var(--t1-bg)", "var(--t1-border)")}>
                            <span style={{ flex: 1, font: "500 11.5px/1.4 var(--font-interface)", color: "var(--alert-ink)" }}>
                              {h?.display_code ?? id.slice(0, 8)} · {h?.population_count ?? "?"} residents inside polygon
                            </span>
                            {h && h.assistance_needs_count > 0 && (
                              <span style={{ font: "500 10px/1 var(--font-data)", color: "var(--sev2-ink)" }}>{h.assistance_needs_count} need assistance</span>
                            )}
                          </div>
                        );
                      })}
                      {latest.cross_referenced_survey_ids.map((id) => {
                        const s = surveys?.find((sv) => sv.survey_id === id);
                        return (
                          <div key={id} style={xrefRowStyle("var(--t2-bg)", "var(--t2-border)")}>
                            <span style={{ flex: 1, font: "500 11.5px/1.4 var(--font-interface)", color: "var(--warn-ink)" }}>
                              Survey {s?.display_code ?? id.slice(0, 8)} within polygon
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ marginTop: 12, font: "400 10.5px/1.6 var(--font-data)", color: "var(--ink4)" }}>
                      This is what turns a change polygon into an actionable line: not just where the impact is, but who is
                      inside it.
                    </div>
                  </div>
                </div>
                <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: "14px 15px" }}>
                  <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 10 }}>
                    Honest scope
                  </div>
                  <div style={{ font: "400 11.5px/1.6 var(--font-data)", color: "var(--ink3)" }}>
                    The differencing algorithm is real and runs against a genuinely generated before/after pair — not a stock
                    photo. What isn't built is the always-on watcher that fires the moment a new satellite pass lands; that
                    needs production infrastructure, so the demo runs on one curated pair instead.
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ font: "500 9.5px/1 var(--font-data)", letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 6 }}>{label}</div>
      <div style={{ font: "600 20px/1 var(--font-data)", color: "var(--ink)" }}>{value}</div>
    </div>
  );
}

function xrefRowStyle(bg: string, border: string) {
  return {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "9px 11px",
    borderRadius: 4,
    background: bg,
    border: `1px solid ${border}`,
  } as const;
}

const runButtonStyle = {
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
