import { useEffect, useState } from "react";

import FactorsPanel from "../components/FactorsPanel";
import { ConfidenceBadge, SampleDataBadge, TierBadge } from "../components/badges";
import {
  createRelocation,
  fetchShelterMatches,
  fetchZoneHouseholds,
  fetchZones,
  type HouseholdRanked,
  type ShelterMatch,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";

/** PRD §7.3 — smart relocation priority ranking: one merged, ranked list
 * across every zone this account can see (not per-zone, unlike household
 * assessment), with the tier thresholds and factor breakdown, plus the
 * shelter-matching + allocate action (PRD §7.4/§7.5) so a ranked
 * household actually turns into a relocation decision from here. */
export default function PriorityRanking() {
  const { token, user } = useAuth();
  const [households, setHouseholds] = useState<HouseholdRanked[] | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [matches, setMatches] = useState<Record<string, ShelterMatch[]>>({});
  const [matchError, setMatchError] = useState<string | null>(null);
  const [allocating, setAllocating] = useState<string | null>(null);
  const [allocated, setAllocated] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const canAllocate = user?.role === "sdma_official";

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchZones(token)
      .then(async (r) => {
        const perZone = await Promise.all(r.items.map((z) => fetchZoneHouseholds(token, z.zone_id).catch(() => ({ items: [] }))));
        if (cancelled) return;
        const all = perZone.flatMap((x) => x.items).sort((a, b) => b.priority_score - a.priority_score);
        setHouseholds(all);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [token]);

  const showMatches = async (householdId: string) => {
    if (expanded === householdId) {
      setExpanded(null);
      return;
    }
    setExpanded(householdId);
    if (!token || matches[householdId]) return;
    try {
      const r = await fetchShelterMatches(token, householdId);
      setMatches((m) => ({ ...m, [householdId]: r.items }));
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : String(err));
    }
  };

  const allocate = async (householdId: string, shelterId: string) => {
    if (!token) return;
    setAllocating(householdId);
    setMatchError(null);
    try {
      const record = await createRelocation(token, { household_id: householdId, shelter_id: shelterId });
      setAllocated((a) => ({ ...a, [householdId]: record.display_code ?? record.record_id }));
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : String(err));
    } finally {
      setAllocating(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load priority ranking: {error}</p>;
  if (!households) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading priority ranking…</p>;

  return (
    <div style={{ padding: 18, maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 18 }}>Priority ranking</h2>
        <SampleDataBadge />
      </div>
      {matchError && <p style={{ color: "var(--sev1)", fontSize: 12, marginBottom: 8 }}>{matchError}</p>}
      <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
        {households.map((h) => (
          <div key={h.household_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <button
              onClick={() => showMatches(h.household_id)}
              className="ps-row-hover"
              style={{ width: "100%", textAlign: "left", background: "transparent", border: 0, cursor: "pointer", padding: "12px 16px" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>{h.display_code}</span>
                <TierBadge tier={h.priority_tier} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                <ConfidenceBadge confidence={h.data_confidence} />
                <span style={{ font: "500 12px/1 var(--font-data)", color: "var(--ink3)" }}>
                  priority {Math.round(h.priority_score * 100)} · vuln {Math.round(h.vulnerability_score * 100)}
                </span>
              </div>
            </button>
            {expanded === h.household_id && (
              <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 14 }}>
                <FactorsPanel title="Priority factors" factors={h.priority_factors} />
                <FactorsPanel title="Vulnerability factors" factors={h.vulnerability_factors} />

                <div>
                  <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 8 }}>
                    Shelter matches
                  </div>
                  {allocated[h.household_id] && (
                    <p style={{ fontSize: 12, color: "var(--sev5)", marginBottom: 8 }}>
                      Allocated · relocation record {allocated[h.household_id]}
                    </p>
                  )}
                  {!matches[h.household_id] && <p style={{ fontSize: 12, color: "var(--ink3)" }}>Loading matches…</p>}
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {matches[h.household_id]?.map((m) => (
                      <div
                        key={m.shelter_id}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          background: "var(--panel2)",
                          border: "1px solid var(--border)",
                          borderRadius: 5,
                          padding: "8px 12px",
                        }}
                      >
                        <div>
                          <div style={{ font: "600 12px/1.3 var(--font-interface)", color: "var(--ink)" }}>{m.display_code} · {m.name}</div>
                          <div style={{ font: "400 10.5px/1.4 var(--font-data)", color: "var(--ink4)" }}>
                            match {Math.round(m.match_score * 100)} · {m.distance_km.toFixed(1)} km · {Math.round(m.duration_minutes)} min ·{" "}
                            {m.route_access} route · {m.current_occupancy}/{m.max_capacity}
                          </div>
                        </div>
                        {canAllocate && !allocated[h.household_id] && (
                          <button
                            onClick={() => allocate(h.household_id, m.shelter_id)}
                            disabled={allocating === h.household_id}
                            className="ps-btn-confirm"
                            style={allocateButtonStyle}
                          >
                            {allocating === h.household_id ? "Allocating…" : "Allocate"}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

const allocateButtonStyle = {
  flex: "none",
  padding: "6px 12px",
  borderRadius: 4,
  border: "1px solid var(--sev5)",
  background: "transparent",
  color: "var(--sev5)",
  font: "600 11px/1 var(--font-interface)",
  cursor: "pointer",
} as const;
