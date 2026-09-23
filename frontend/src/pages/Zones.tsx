import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import ZoneMap from "../components/ZoneMap";
import { ConfidenceBadge, RiskChip } from "../components/badges";
import { fetchZones, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { useTheme } from "../lib/ThemeContext";

export default function Zones() {
  const { token } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchZones(token)
      .then((r) => {
        if (!cancelled) setZones(r.items);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load zones: {error}</p>;
  if (!zones) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading zones…</p>;

  return (
    <div data-reveal="" style={{ display: "flex", height: "100%" }}>
      <div style={{ flex: 1.4, position: "relative", borderRight: "1px solid var(--border)" }}>
        <ZoneMap zones={zones} theme={theme} onSelectZone={(zoneId) => navigate(`/zones/${zoneId}`)} />
      </div>
      <div style={{ flex: 1, minWidth: 380, maxWidth: 520, overflow: "auto" }}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <span style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>
            Red zone register
          </span>
        </div>
        {zones.map((z) => (
          <button
            key={z.zone_id}
            onClick={() => navigate(`/zones/${z.zone_id}`)}
            className="ps-row-hover"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              width: "100%",
              padding: "12px 16px",
              border: 0,
              borderBottom: "1px solid var(--border-soft)",
              background: "transparent",
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ font: "600 13px/1.3 var(--font-interface)", color: "var(--ink)" }}>
                {z.display_code} · {z.name}
              </span>
              <RiskChip score={z.risk_score_72h} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ font: "400 11px/1.4 var(--font-data)", color: "var(--ink4)" }}>
                {z.hazard_types.join(", ")} · {z.population.toLocaleString("en-IN")} residents
              </span>
              <ConfidenceBadge confidence={z.data_confidence} />
            </div>
            {z.gsi_classification && (
              <div style={{ font: "400 10.5px/1.4 var(--font-data)", color: "var(--ink4)" }}>
                GSI: {z.gsi_classification}
                {z.gsi_score !== null ? ` (${z.gsi_score})` : ""}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
