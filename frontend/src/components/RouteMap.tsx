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

// Fixed, theme-independent — these render in Leaflet's marker pane, which
// (unlike .leaflet-tile-pane) ZoneMap.tsx's dark-mode invert filter never
// touches, so a hardcoded color always renders as-is on both basemaps.
const ORIGIN_COLOR = "#FD9E02"; // zone/origin — matches riskColor.ts's sev3 amber
const DEST_COLOR = "#22C55E"; // shelter/destination — a safe-arrival green

export interface RouteMapEntry extends RouteRecord {
  /** e.g. "ZN-01 · Upper Ridge" — shown on the origin marker's tooltip/popup. */
  originLabel?: string;
  /** e.g. "SH-01 · Ridge Higher Secondary School" — on the destination marker. */
  destLabel?: string;
}

function pathLatLngs(path: RouteRecord["path"]): L.LatLngExpression[] {
  return (path.coordinates as [number, number][]).map(([lon, lat]) => [lat, lon]);
}

function dotIcon(color: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function shelterIcon(color: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div style="width:24px;height:24px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;font-size:13px;line-height:1">🏠</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

/** Simplified sibling of ZoneMap for route LineStrings — no tile-fallback
 * chain (routes are a supporting view, not the primary red-zone map that
 * needs to survive a flaky link at all costs). Draws exactly the routes
 * it's given — the caller (pages/Routes.tsx) is responsible for passing
 * only the currently-selected one, so this component doesn't need its own
 * notion of "selected" at all. */
export default function RouteMap({ routes, theme = "dark" }: { routes: RouteMapEntry[]; theme?: Theme }) {
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
      const latLngs = pathLatLngs(route.path);
      const line = L.polyline(latLngs, {
        color: blocked ? colors.blocked : colors.clear,
        weight: 4,
        opacity: 0.9,
      }).addTo(map);
      line.bindTooltip(`${route.display_code ?? route.route_id} · ${blocked ? "blocked" : "clear"}`, { sticky: true });
      layers.push(line);

      // Markers sit at the *drawn line's own* two ends, not at
      // origin_geom/dest_geom directly — those are the raw zone centroid
      // and shelter point, which OSRM's road-snapping can leave several
      // km from where the actual route geometry starts/ends (a zone
      // centroid placed off-road snaps to the nearest real road). Using
      // the path's own endpoints guarantees a marker is always exactly on
      // the line it belongs to, whichever geometry source produced it.
      const origin = L.marker(latLngs[0], { icon: dotIcon(ORIGIN_COLOR) }).addTo(map);
      const originLabel = route.originLabel ?? "Origin";
      origin.bindTooltip(originLabel, { direction: "top", offset: [0, -8] });
      origin.bindPopup(`<b>Start</b><br>${originLabel}`);
      layers.push(origin);

      const dest = L.marker(latLngs[latLngs.length - 1], { icon: shelterIcon(DEST_COLOR) }).addTo(map);
      const destLabel = route.destLabel ?? "Shelter";
      dest.bindTooltip(destLabel, { direction: "top", offset: [0, -12] });
      dest.bindPopup(`<b>Shelter</b><br>${destLabel}`);
      layers.push(dest);
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
