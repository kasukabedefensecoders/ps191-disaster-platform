import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

import type { RouteRecord } from "../lib/api";
import type { Theme } from "../lib/ThemeContext";

const OSM_URL = "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png";

const ROUTE_COLOR: Record<Theme, { blocked: string; clear: string }> = {
  dark: { blocked: "#B80C09", clear: "#32E875" },
  light: { blocked: "#D32E22", clear: "#2E8A7D" },
};

function pathLatLngs(path: RouteRecord["path"]): L.LatLngExpression[] {
  return (path.coordinates as [number, number][]).map(([lon, lat]) => [lat, lon]);
}

/** Simplified sibling of ZoneMap for route LineStrings — no tile-fallback
 * chain (routes are a supporting view, not the primary red-zone map that
 * needs to survive a flaky link at all costs). */
export default function RouteMap({ routes, theme = "dark" }: { routes: RouteRecord[]; theme?: Theme }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = L.map(containerRef.current, { zoomControl: true, attributionControl: true });
    mapRef.current = map;
    L.tileLayer(OSM_URL, { attribution: "© OpenStreetMap contributors", maxZoom: 18, subdomains: "abc" }).addTo(map);
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const colors = ROUTE_COLOR[theme];
    const layers: L.Layer[] = [];
    routes.forEach((route) => {
      const blocked = route.blocked_segments.length > 0;
      const line = L.polyline(pathLatLngs(route.path), {
        color: blocked ? colors.blocked : colors.clear,
        weight: 3,
        opacity: 0.9,
      }).addTo(map);
      line.bindTooltip(`${route.display_code ?? route.route_id} · ${blocked ? "blocked" : "clear"}`, { sticky: true });
      layers.push(line);
    });

    if (routes.length > 0) {
      const bounds = L.latLngBounds(routes.flatMap((r) => pathLatLngs(r.path)));
      map.fitBounds(bounds.pad(0.2));
    }

    return () => {
      layers.forEach((l) => map.removeLayer(l));
    };
  }, [routes, theme]);

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}
