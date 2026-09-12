import { useEffect, useState } from "react";

import { SampleDataBadge } from "../components/badges";
import { fetchShelters, type Shelter } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

export default function Shelters() {
  const { token } = useAuth();
  const [shelters, setShelters] = useState<Shelter[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchShelters(token)
      .then((r) => {
        if (!cancelled) setShelters(r.items);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load shelters: {error}</p>;
  if (!shelters) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading shelters…</p>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ fontSize: 14, margin: 0 }}>Shelters</h2>
        <SampleDataBadge />
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--ink4)", fontSize: 11, textTransform: "uppercase" }}>
            <th style={th}>Code</th>
            <th style={th}>Name</th>
            <th style={th}>Occupancy</th>
            <th style={th}>Facilities</th>
            <th style={th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {shelters.map((s) => {
            const pct = Math.round((s.current_occupancy / s.max_capacity) * 100);
            return (
              <tr key={s.shelter_id} style={{ borderTop: "1px solid var(--border-soft)" }}>
                <td style={{ ...td, fontFamily: "var(--font-data)" }}>{s.display_code}</td>
                <td style={td}>{s.name}</td>
                <td style={{ ...td, fontFamily: "var(--font-data)" }}>
                  {s.current_occupancy}/{s.max_capacity} ({pct}%)
                </td>
                <td style={td}>
                  {Object.entries(s.facilities)
                    .filter(([k, v]) => k !== "other" && v === true)
                    .map(([k]) => k)
                    .join(", ") || "—"}
                </td>
                <td style={td}>{s.status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const th = { padding: "6px 8px" };
const td = { padding: "8px" };
