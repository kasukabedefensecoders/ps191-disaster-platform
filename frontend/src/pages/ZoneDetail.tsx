import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import FactorsPanel from "../components/FactorsPanel";
import ZoneMap from "../components/ZoneMap";
import { ConfidenceBadge, RiskChip, SampleDataBadge, TierBadge } from "../components/badges";
import {
  fetchZone,
  fetchZoneChangeDetections,
  fetchZoneForecasts,
  fetchZoneHouseholds,
  generateForecasts,
  runChangeDetection,
  type ChangeDetection,
  type HouseholdRanked,
  type RiskForecast,
  type ZoneDetail as ZoneDetailType,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { useTheme } from "../lib/ThemeContext";

const HORIZONS = [6, 12, 24, 36, 48, 72];

export default function ZoneDetail() {
  const { zoneId } = useParams<{ zoneId: string }>();
  const { token, user } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();

  const [zone, setZone] = useState<ZoneDetailType | null>(null);
  const [households, setHouseholds] = useState<HouseholdRanked[] | null>(null);
  const [forecasts, setForecasts] = useState<RiskForecast[] | null>(null);
  const [detections, setDetections] = useState<ChangeDetection[] | null>(null);
  const [expandedHousehold, setExpandedHousehold] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const canWrite = user?.role === "sdma_official";

  const load = () => {
    if (!token || !zoneId) return;
    fetchZone(token, zoneId)
      .then(setZone)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    fetchZoneHouseholds(token, zoneId)
      .then((r) => setHouseholds(r.items))
      .catch(() => {});
    fetchZoneForecasts(token, zoneId)
      .then((r) => setForecasts(r.items))
      .catch(() => {});
    fetchZoneChangeDetections(token, zoneId)
      .then((r) => setDetections(r.items))
      .catch(() => {});
  };

  useEffect(load, [token, zoneId]);

  const runGenerateForecasts = async () => {
    if (!token || !zoneId) return;
    setBusy("forecast");
    setError(null);
    try {
      await generateForecasts(token, zoneId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const runDetection = async () => {
    if (!token || !zoneId) return;
    setBusy("detection");
    setError(null);
    try {
      await runChangeDetection(token, zoneId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  if (!zoneId) return null;
  if (!zone) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading zone…</p>;

  const latestByHorizon = new Map<number, RiskForecast>();
  for (const f of forecasts ?? []) {
    const existing = latestByHorizon.get(f.horizon_hours);
    if (!existing || f.generated_at > existing.generated_at) latestByHorizon.set(f.horizon_hours, f);
  }
  const peak = [...latestByHorizon.values()].reduce<RiskForecast | null>(
    (max, f) => (!max || f.score > max.score ? f : max),
    null,
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "auto" }}>
      <div style={{ padding: 16, borderBottom: "1px solid var(--border)" }}>
        <button onClick={() => navigate("/zones")} style={backLinkStyle}>
          ← All zones
        </button>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginTop: 8 }}>
          <div>
            <h2 style={{ fontSize: 20 }}>
              {zone.display_code} · {zone.name}
            </h2>
            <div style={{ display: "flex", gap: 14, alignItems: "center", marginTop: 6, fontSize: 12, color: "var(--ink3)" }}>
              <ConfidenceBadge confidence={zone.data_confidence} />
              <span>{zone.hazard_types.join(", ")}</span>
              <span style={{ fontFamily: "var(--font-data)" }}>{zone.population.toLocaleString("en-IN")} residents</span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SampleDataBadge />
            <RiskChip score={zone.risk_score_72h} />
          </div>
        </div>
        {zone.ml_vs_gsi_divergence_note && (
          <div style={{ marginTop: 10, fontSize: 12, color: "var(--ink2)", background: "var(--panel2)", border: "1px solid var(--border)", padding: 10 }}>
            <span style={{ fontFamily: "var(--font-data)", fontSize: 10, letterSpacing: "0.04em", color: "var(--ink4)", textTransform: "uppercase" }}>
              ML vs GSI divergence
            </span>
            <p style={{ margin: "4px 0 0" }}>{zone.ml_vs_gsi_divergence_note}</p>
          </div>
        )}
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 480 }}>
        <div style={{ flex: 1, position: "relative", borderRight: "1px solid var(--border)" }}>
          <ZoneMap zones={[zone]} theme={theme} />
        </div>

        <div style={{ flex: 1, minWidth: 380, maxWidth: 480, padding: 16, display: "flex", flexDirection: "column", gap: 20, overflow: "auto" }}>
          {error && <p style={{ color: "var(--sev1)", fontSize: 12 }}>{error}</p>}

          <Section
            title="72-hour forecast"
            action={
              canWrite && (
                <button onClick={runGenerateForecasts} disabled={busy === "forecast"} className="ps-btn-primary" style={actionButtonStyle}>
                  {busy === "forecast" ? (
                    <>
                      <span className="ps-spinner" /> Generating…
                    </>
                  ) : (
                    "Generate"
                  )}
                </button>
              )
            }
          >
            {latestByHorizon.size === 0 && <p style={emptyText}>No forecast cycle run yet for this zone.</p>}
            {latestByHorizon.size > 0 && (
              <div key={peak?.generated_at} data-reveal="">
                <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6 }}>
                  {HORIZONS.map((h) => {
                    const f = latestByHorizon.get(h);
                    return (
                      <div key={h} style={{ textAlign: "center", padding: "6px 2px", background: "var(--panel2)", border: "1px solid var(--border)", borderRadius: 4 }}>
                        <div style={{ fontSize: 9, color: "var(--ink4)", fontFamily: "var(--font-data)" }}>{h}h</div>
                        <div style={{ fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 13 }}>
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
          </Section>

          <Section
            title="SAR change detection"
            action={
              canWrite && (
                <button onClick={runDetection} disabled={busy === "detection"} className="ps-btn-primary" style={actionButtonStyle}>
                  {busy === "detection" ? "Running…" : "Run detection"}
                </button>
              )
            }
          >
            {(!detections || detections.length === 0) && <p style={emptyText}>No change-detection run recorded for this zone.</p>}
            {detections?.map((d) => (
              <div key={d.detection_id} style={{ fontSize: 12, padding: "8px 0", borderTop: "1px solid var(--border-soft)" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{new Date(d.detected_at).toLocaleString()}</span>
                  <span style={{ fontFamily: "var(--font-data)" }}>
                    confidence {d.confidence !== null ? Math.round(d.confidence * 100) : "—"}
                  </span>
                </div>
                <div style={{ color: "var(--ink3)", marginTop: 2 }}>
                  {d.cross_referenced_household_ids.length} household(s) · {d.cross_referenced_survey_ids.length} survey(s) in affected area
                </div>
              </div>
            ))}
          </Section>

          <Section title="Priority ranking">
            {(!households || households.length === 0) && <p style={emptyText}>No households on record for this zone.</p>}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {households?.map((h) => (
                <div key={h.household_id} style={{ background: "var(--panel2)", border: "1px solid var(--border)", borderRadius: 5, overflow: "hidden" }}>
                  <button
                    onClick={() => setExpandedHousehold(expandedHousehold === h.household_id ? null : h.household_id)}
                    className="ps-row-hover"
                    style={householdRowStyle}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-data)", fontWeight: 600 }}>{h.display_code}</span>
                      <TierBadge tier={h.priority_tier} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                      <ConfidenceBadge confidence={h.data_confidence} />
                      <span style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink3)" }}>
                        priority {Math.round(h.priority_score * 100)} · vuln {Math.round(h.vulnerability_score * 100)}
                      </span>
                    </div>
                  </button>
                  {expandedHousehold === h.household_id && (
                    <div style={{ padding: "0 10px 12px", display: "flex", flexDirection: "column", gap: 12 }}>
                      <FactorsPanel title="Priority factors" factors={h.priority_factors} />
                      <FactorsPanel title="Vulnerability factors" factors={h.vulnerability_factors} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>

          <Link to={`/incident-outcomes?zone=${zone.zone_id}`} style={{ fontSize: 12, color: "var(--accent)" }}>
            View post-incident feedback for this zone →
          </Link>
        </div>
      </div>
    </div>
  );
}

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <span style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>
          {title}
        </span>
        {action}
      </div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  );
}

const backLinkStyle: CSSProperties = {
  background: "transparent",
  border: "none",
  color: "var(--ink3)",
  fontSize: 12,
  cursor: "pointer",
  padding: 0,
};
const actionButtonStyle: CSSProperties = {
  background: "var(--accent)",
  color: "var(--on-accent)",
  border: "1px solid var(--accent)",
  borderRadius: 4,
  padding: "5px 11px",
  fontSize: 11,
  fontWeight: 600,
  fontFamily: "var(--font-interface)",
  cursor: "pointer",
};
const householdRowStyle: CSSProperties = {
  width: "100%",
  textAlign: "left",
  background: "transparent",
  border: "none",
  color: "inherit",
  cursor: "pointer",
  padding: 10,
};
const emptyText: CSSProperties = { fontSize: 12, color: "var(--ink3)" };
