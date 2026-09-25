import { useEffect, useState, type CSSProperties } from "react";

import RouteMap from "../components/RouteMap";
import { SampleDataBadge } from "../components/badges";
import { addBlockedSegment, clearBlockedSegments, fetchRoutes, fetchShelters, fetchZones, type RouteRecord, type Shelter, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { useTheme } from "../lib/ThemeContext";

export default function RoutesPage() {
  const { token, user } = useAuth();
  const { theme } = useTheme();
  const [routes, setRoutes] = useState<RouteRecord[] | null>(null);
  const [zonesById, setZonesById] = useState<Record<string, Zone>>({});
  const [sheltersById, setSheltersById] = useState<Record<string, Shelter>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [reasonDraft, setReasonDraft] = useState<Record<string, string>>({});

  const load = () => {
    if (!token) return;
    fetchRoutes(token)
      .then((r) => setRoutes(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    fetchZones(token)
      .then((r) => setZonesById(Object.fromEntries(r.items.map((z) => [z.zone_id, z]))))
      .catch(() => {});
    fetchShelters(token)
      .then((r) => setSheltersById(Object.fromEntries(r.items.map((s) => [s.shelter_id, s]))))
      .catch(() => {});
  };

  useEffect(load, [token]);

  const report = async (routeId: string) => {
    if (!token) return;
    const reason = (reasonDraft[routeId] ?? "").trim();
    if (!reason) return;
    setBusyId(routeId);
    try {
      await addBlockedSegment(token, routeId, { reason });
      setReasonDraft((d) => ({ ...d, [routeId]: "" }));
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const clear = async (routeId: string) => {
    if (!token) return;
    setBusyId(routeId);
    try {
      await clearBlockedSegments(token, routeId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load routes: {error}</p>;
  if (!routes) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading routes…</p>;

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <div style={{ flex: 2, position: "relative", borderRight: "1px solid var(--border)" }}>
        <RouteMap routes={routes} theme={theme} />
        <div style={{ position: "absolute", left: 10, bottom: 10, zIndex: 500 }}>
          <SampleDataBadge />
        </div>
      </div>
      <div style={{ flex: 1, minWidth: 360, maxWidth: 440, overflow: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Evacuation routes</h2>
        {routes.length === 0 && <p style={{ fontSize: 12, color: "var(--ink3)" }}>No routes recorded.</p>}
        {[...routes]
          .sort((a, b) => (zonesById[a.zone_id]?.display_code ?? "").localeCompare(zonesById[b.zone_id]?.display_code ?? ""))
          .map((r) => {
          const blocked = r.blocked_segments.length > 0;
          const zone = zonesById[r.zone_id];
          const shelter = sheltersById[r.shelter_id];
          return (
            <div key={r.route_id} className="ps-card-hover" style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "var(--font-data)", fontWeight: 600 }}>{r.display_code}</span>
                <span style={{ fontFamily: "var(--font-data)", fontSize: 11, color: blocked ? "var(--sev1)" : "var(--sev5)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {blocked ? "Blocked" : "Clear"}
                </span>
              </div>
              {zone && (
                <div style={{ fontSize: 11, color: "var(--ink4)" }}>
                  For {zone.display_code} · {zone.name}
                </div>
              )}
              {shelter && (
                <div style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink2)" }}>
                  → {shelter.display_code} · {shelter.name}
                </div>
              )}
              <div style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink3)" }}>
                {r.distance_km !== null ? `${r.distance_km.toFixed(1)} km` : "distance unknown"}
                {r.estimated_duration_minutes !== null ? ` · ${r.estimated_duration_minutes} min` : ""}
              </div>
              {r.blocked_segments.map((seg, i) => (
                <div key={i} style={{ fontSize: 11, color: "var(--ink2)", background: "var(--panel2)", borderRadius: 4, padding: "4px 6px" }}>
                  {String(seg.reason)} <span style={{ color: "var(--ink4)" }}>({String(seg.source)})</span>
                </div>
              ))}
              <div style={{ display: "flex", gap: 6 }}>
                <input
                  placeholder="Report a blockage…"
                  value={reasonDraft[r.route_id] ?? ""}
                  onChange={(e) => setReasonDraft((d) => ({ ...d, [r.route_id]: e.target.value }))}
                  style={{ flex: 1, background: "var(--panel2)", border: "1px solid var(--border2)", borderRadius: 4, color: "var(--ink2)", padding: "5px 8px", fontSize: 12 }}
                />
                <button onClick={() => report(r.route_id)} disabled={busyId === r.route_id} className="ps-icon-btn" style={smallButtonStyle}>
                  Report
                </button>
                {blocked && user?.role === "sdma_official" && (
                  <button onClick={() => clear(r.route_id)} disabled={busyId === r.route_id} className="ps-icon-btn" style={smallButtonStyle}>
                    Clear
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const smallButtonStyle: CSSProperties = {
  background: "transparent",
  border: "1px solid var(--border2)",
  borderRadius: 4,
  color: "var(--ink2)",
  padding: "5px 10px",
  fontSize: 12,
  cursor: "pointer",
  flex: "none",
};
