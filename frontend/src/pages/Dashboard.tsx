import { useEffect, useState } from "react";

import FactorsPanel from "../components/FactorsPanel";
import ZoneMap from "../components/ZoneMap";
import { ConfidenceBadge, HandoffStatusBadge, SampleDataBadge, TierBadge } from "../components/badges";
import { fetchDashboardSummary, type DashboardSummary, type HouseholdRanked } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

export default function Dashboard() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchDashboardSummary(token)
      .then((s) => {
        if (!cancelled) setSummary(s);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load dashboard: {error}</p>;
  if (!summary) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading dashboard…</p>;

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <div style={{ flex: 2, position: "relative", borderRight: "1px solid var(--border)" }}>
        <ZoneMap zones={summary.zones.items} />
      </div>
      <div style={{ flex: 1, minWidth: 340, maxWidth: 420, overflow: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ fontSize: 14, margin: 0 }}>Priority queue</h2>
            <SampleDataBadge />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {summary.top_priority_households.map((h) => (
              <HouseholdCard
                key={h.household_id}
                household={h}
                expanded={expanded === h.household_id}
                onToggle={() => setExpanded(expanded === h.household_id ? null : h.household_id)}
              />
            ))}
          </div>
        </div>

        <div>
          <h2 style={{ fontSize: 14, margin: "0 0 12px" }}>Interagency handoffs</h2>
          {summary.handoffs.items.length === 0 && <p style={{ fontSize: 12, color: "var(--ink3)" }}>No open needs.</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {summary.handoffs.items.map((h) => (
              <div
                key={h.log_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "8px 10px",
                  fontSize: 12,
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
                  <span style={{ fontFamily: "var(--font-data)", fontWeight: 600 }}>
                    {h.display_code} · {h.need_type}
                  </span>
                  <span style={{ color: "var(--ink3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.agency}</span>
                </div>
                <HandoffStatusBadge status={h.status} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function HouseholdCard({
  household,
  expanded,
  onToggle,
}: {
  household: HouseholdRanked;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          textAlign: "left",
          background: "transparent",
          border: "none",
          color: "inherit",
          cursor: "pointer",
          padding: 10,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: "var(--font-data)", fontSize: 12, fontWeight: 600 }}>{household.display_code}</span>
          <TierBadge tier={household.priority_tier} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <ConfidenceBadge confidence={household.data_confidence} />
          <span style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink3)" }}>
            priority {Math.round(household.priority_score * 100)}
          </span>
        </div>
      </button>
      {expanded && (
        <div style={{ padding: "0 10px 12px", display: "flex", flexDirection: "column", gap: 12 }}>
          <FactorsPanel title="Priority factors" factors={household.priority_factors} />
          <FactorsPanel title="Vulnerability factors" factors={household.vulnerability_factors} />
        </div>
      )}
    </div>
  );
}
