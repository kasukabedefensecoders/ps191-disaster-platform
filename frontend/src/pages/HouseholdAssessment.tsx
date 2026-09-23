import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import FactorsPanel from "../components/FactorsPanel";
import { ConfidenceBadge, SampleDataBadge } from "../components/badges";
import { fetchZoneHouseholds, fetchZones, type HouseholdRanked, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

/** Tri-band label for a zone's risk_score_72h, distinct from riskColor.ts's
 * 5-band raw-risk palette (docs/DESIGN-SYSTEM.md §2.3) — this screen only
 * needs enough resolution to sort red zones to the top, not the full scale. */
function riskBand(score: number | null): { label: string; bg: string; border: string; ink: string } {
  const risk = score ?? 0;
  if (risk >= 0.65) return { label: "RED", bg: "var(--t1-bg)", border: "var(--t1-border)", ink: "var(--sev2-ink)" };
  if (risk >= 0.4) return { label: "YELLOW", bg: "var(--t2-bg)", border: "var(--t2-border)", ink: "var(--sev3-ink)" };
  return { label: "GREEN", bg: "var(--ok-bg)", border: "var(--ok-border)", ink: "var(--sev5-ink)" };
}

/** PRD §7.2 — household assessment: every household this account can see,
 * grouped by zone, with the vulnerability score and full factor
 * breakdown. Zones sort highest-risk first and collapse independently
 * (Change 1) so a district with many zones doesn't dump every household
 * on screen at once — only the top-risk zone opens by default. */
export default function HouseholdAssessment() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [byZone, setByZone] = useState<Record<string, HouseholdRanked[]>>({});
  const [expandedZones, setExpandedZones] = useState<Set<string>>(new Set());
  const [expandedHousehold, setExpandedHousehold] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchZones(token)
      .then(async (r) => {
        if (cancelled) return;
        const sorted = [...r.items].sort((a, b) => (b.risk_score_72h ?? 0) - (a.risk_score_72h ?? 0));
        setZones(sorted);
        if (sorted.length > 0) setExpandedZones(new Set([sorted[0].zone_id]));
        const entries = await Promise.all(
          sorted.map(async (z) => [z.zone_id, (await fetchZoneHouseholds(token, z.zone_id).catch(() => ({ items: [] }))).items] as const),
        );
        if (!cancelled) setByZone(Object.fromEntries(entries));
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [token]);

  const toggleZone = (zoneId: string) => {
    setExpandedZones((prev) => {
      const next = new Set(prev);
      if (next.has(zoneId)) next.delete(zoneId);
      else next.add(zoneId);
      return next;
    });
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load households: {error}</p>;
  if (!zones) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading households…</p>;

  return (
    <div style={{ padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 18 }}>Household assessment</h2>
        <SampleDataBadge />
      </div>
      {zones.map((z) => {
        const households = byZone[z.zone_id] ?? [];
        const expanded = expandedZones.has(z.zone_id);
        const band = riskBand(z.risk_score_72h);
        return (
          <div key={z.zone_id} style={{ marginBottom: 14 }}>
            <button
              onClick={() => toggleZone(z.zone_id)}
              className="ps-row-hover"
              style={{
                width: "100%",
                textAlign: "left",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "12px 14px",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ font: "500 10px/1 var(--font-data)", color: "var(--ink4)", width: 12 }}>{expanded ? "▼" : "▶"}</span>
                <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>{z.display_code} · {z.name}</span>
                <span
                  style={{
                    font: "600 9px/1 var(--font-data)",
                    letterSpacing: "0.06em",
                    padding: "3px 6px",
                    borderRadius: 3,
                    background: band.bg,
                    border: `1px solid ${band.border}`,
                    color: band.ink,
                  }}
                >
                  {band.label}
                </span>
                <span style={{ font: "400 11px/1 var(--font-data)", color: "var(--ink4)" }}>({households.length} households)</span>
              </div>
              <ConfidenceBadge confidence={z.data_confidence} />
            </button>

            {expanded && (
              <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderTop: "none", borderRadius: "0 0 6px 6px", overflow: "hidden" }}>
                {households.length === 0 && <p style={{ padding: 16, fontSize: 12, color: "var(--ink3)" }}>No households on record.</p>}
                {households.map((h) => (
                  <div key={h.household_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                    <div
                      className="ps-row-hover"
                      style={{ display: "flex", alignItems: "stretch" }}
                    >
                      <button
                        onClick={() => setExpandedHousehold(expandedHousehold === h.household_id ? null : h.household_id)}
                        style={{ flex: 1, textAlign: "left", background: "transparent", border: 0, cursor: "pointer", padding: "12px 16px" }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>{h.display_code}</span>
                          <span style={{ font: "600 15px/1.1 var(--font-data)", color: "var(--sev2-ink)" }}>{Math.round(h.vulnerability_score * 100)}</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                          <span style={{ font: "400 11px/1.4 var(--font-data)", color: "var(--ink4)" }}>
                            {h.structural_condition} · {h.population_count} residents · {h.children_count} children · {h.elderly_count} elderly ·{" "}
                            {h.assistance_needs_count} need assistance
                          </span>
                          <ConfidenceBadge confidence={h.data_confidence} />
                        </div>
                      </button>
                      <button
                        onClick={() => navigate("/shelters", { state: { household: h } })}
                        className="ps-btn-outline"
                        style={{
                          flex: "none",
                          margin: "12px 16px 12px 0",
                          padding: "6px 12px",
                          borderRadius: 4,
                          border: "1px solid var(--accent)",
                          background: "transparent",
                          color: "var(--accent)",
                          font: "600 11px/1 var(--font-interface)",
                          cursor: "pointer",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Allocate to shelter →
                      </button>
                    </div>
                    {expandedHousehold === h.household_id && (
                      <div style={{ padding: "0 16px 14px" }}>
                        <FactorsPanel title="Vulnerability factors" factors={h.vulnerability_factors} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
