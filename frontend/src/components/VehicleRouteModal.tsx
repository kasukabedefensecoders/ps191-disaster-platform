import { useEffect, useState } from "react";

import type { GeoJSONLineString } from "../lib/api";
import { fetchOsrmRoute } from "../lib/osrm";
import { useTheme } from "../lib/ThemeContext";
import RouteMap, { type RouteMapEntry } from "./RouteMap";

function haversineKm(a: [number, number], b: [number, number]): number {
  const R = 6371.0088;
  const [lon1, lat1] = a;
  const [lon2, lat2] = b;
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dphi = ((lat2 - lat1) * Math.PI) / 180;
  const dlmb = ((lon2 - lon1) * Math.PI) / 180;
  const x = Math.sin(dphi / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dlmb / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

/** Logistics Tracker's "View Route" — same OSRM call and the same RouteMap
 * component the Evacuation Routes page uses, not a second implementation.
 * Unlike an evacuation route, a vehicle's pickup point isn't necessarily
 * one of the seeded zone->shelter `routes` rows (a bus can consolidate
 * households from several zones, or go to a different shelter than that
 * zone's own evacuation route does — see demo_seed.py's VEHICLE_PLAN), so
 * this always computes a fresh OSRM route between the vehicle's actual
 * pickup point and drop-off shelter rather than trying to match one. */
export default function VehicleRouteModal({
  title,
  originLabel,
  destLabel,
  origin,
  dest,
  onClose,
}: {
  title: string;
  originLabel: string;
  destLabel: string;
  origin: [number, number];
  dest: [number, number];
  onClose: () => void;
}) {
  const { theme } = useTheme();
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [route, setRoute] = useState<{ path: GeoJSONLineString; distance_km: number; duration_minutes: number; approximate: boolean } | null>(null);

  useEffect(() => {
    let live = true;
    fetchOsrmRoute(origin, dest).then((osrm) => {
      if (!live) return;
      if (osrm) {
        setRoute({ ...osrm, approximate: false });
      } else {
        // lib/osrm.ts already logged the console.warn — fall back to a
        // straight line between the same two points so the modal still
        // shows a connected path rather than breaking.
        setRoute({
          path: { type: "LineString", coordinates: [origin, dest] },
          distance_km: haversineKm(origin, dest),
          duration_minutes: (haversineKm(origin, dest) / 25) * 60,
          approximate: true,
        });
      }
      setStatus("ready");
    });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [origin[0], origin[1], dest[0], dest[1]]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const mapRoutes: RouteMapEntry[] = route
    ? [
        {
          route_id: "vehicle-route-preview",
          display_code: title,
          zone_id: "",
          shelter_id: "",
          origin_geom: { type: "Point", coordinates: origin },
          dest_geom: { type: "Point", coordinates: dest },
          path: route.path,
          blocked_segments: [],
          distance_km: route.distance_km,
          estimated_duration_minutes: Math.round(route.duration_minutes),
          created_at: "",
          updated_at: "",
          originLabel,
          destLabel,
        },
      ]
    : [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      data-modal-overlay=""
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1100,
        background: "rgba(4, 8, 18, 0.6)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        data-modal-card=""
        style={{
          width: "100%",
          maxWidth: 760,
          background: "var(--bg2)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          boxShadow: "var(--shadow)",
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
          <div>
            <div style={{ font: "600 15px/1.3 var(--font-interface)", color: "var(--ink)" }}>{title}</div>
            <div style={{ font: "400 11.5px/1.5 var(--font-data)", color: "var(--ink4)", marginTop: 2 }}>
              {originLabel} → {destLabel}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{ background: "transparent", border: "1px solid var(--border2)", borderRadius: 4, color: "var(--ink3)", width: 26, height: 26, cursor: "pointer", flex: "none" }}
          >
            ✕
          </button>
        </div>

        <div style={{ position: "relative", height: 420, borderRadius: 6, overflow: "hidden", border: "1px solid var(--border)" }}>
          {status === "loading" ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg2)" }}>
              <span style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink4)" }}>Fetching real road route…</span>
            </div>
          ) : (
            <RouteMap routes={mapRoutes} theme={theme} />
          )}
        </div>

        {route && (
          <div style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink3)" }}>
            {route.distance_km.toFixed(1)} km · {Math.round(route.duration_minutes)} min
            {route.approximate && <span style={{ color: "var(--ink4)" }}> — straight-line estimate, live road routing was unavailable</span>}
          </div>
        )}
      </div>
    </div>
  );
}
