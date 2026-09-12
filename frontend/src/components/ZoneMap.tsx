import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";

import type { Zone } from "../lib/api";
import { riskColor, type Theme } from "../lib/riskColor";

/**
 * Leaflet setup ported from PROTOTYPE/dima-hasao-map.html nearly as-is per
 * CLAUDE.md: same tile-fallback chain (OSM -> Esri -> a plain list when
 * both fail), same theme-aware styling approach. What's different: zone
 * polygons come from real backend GeoJSON (zones.geom via GET /zones), not
 * the prototype's synthetic deterministic-heptagon approximation, and
 * colour is docs/DESIGN-SYSTEM.md §2.3's risk-severity scale (--sev1..5)
 * rather than a hardcoded per-zone `tier` field.
 */

const OSM_URL = "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png";
const esriUrl = (theme: Theme) =>
  theme === "light"
    ? "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
    : "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";

function toLatLngs(geom: Zone["geom"]): L.LatLngExpression[] {
  // GeoJSON is [lon, lat]; Leaflet wants [lat, lon]. Only the outer ring —
  // zones.geom is a plain Polygon (Backend Schema §5.3), never a hole.
  return geom.coordinates[0].map(([lon, lat]) => [lat, lon] as L.LatLngExpression);
}

interface ZoneMapProps {
  zones: Zone[];
  theme?: Theme;
  onSelectZone?: (zoneId: string) => void;
}

export default function ZoneMap({ zones, theme = "dark", onSelectZone }: ZoneMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const zoneLayersRef = useRef<L.Polygon[]>([]);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = L.map(containerRef.current, { zoomControl: true, attributionControl: true });
    mapRef.current = map;

    // React 18 StrictMode mounts, cleans up, and remounts every effect once
    // in dev — map.remove() runs between the two. Without this guard, the
    // first mount's 5s fallback timer fires after that cleanup and calls
    // .addTo(map) on an already-torn-down Leaflet map (whose container was
    // ripped out from under it), crashing on a null appendChild. Caught by
    // actually loading the page, not by the type-checker or the test suite.
    let live = true;
    let tileErrorCount = 0;
    let tileLoadCount = 0;
    let escalated = false;

    const setTileLayer = (kind: "osm" | "esri") => {
      if (!live) return;
      if (tileLayerRef.current) map.removeLayer(tileLayerRef.current);
      const layer =
        kind === "osm"
          ? L.tileLayer(OSM_URL, { attribution: "© OpenStreetMap contributors", maxZoom: 18, subdomains: "abc" })
          : L.tileLayer(esriUrl(theme), { attribution: "Tiles © Esri", maxZoom: 16 });
      layer.addTo(map);
      tileLayerRef.current = layer;

      tileLoadCount = 0;
      tileErrorCount = 0;
      layer.on("load", () => {
        tileLoadCount++;
      });
      layer.on("tileerror", () => {
        tileErrorCount++;
        if (tileErrorCount >= 6) escalate(kind);
      });
      setTimeout(() => {
        if (live && tileLoadCount === 0) escalate(kind);
      }, 5000);
    };

    const escalate = (fromKind: "osm" | "esri") => {
      if (!live || escalated) return;
      if (fromKind === "osm") {
        setTileLayer("esri");
      } else {
        escalated = true;
        setFallback(true);
      }
    };

    setTileLayer("osm");

    return () => {
      live = false;
      map.remove();
      mapRef.current = null;
      tileLayerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || fallback) return;

    zoneLayersRef.current.forEach((layer) => map.removeLayer(layer));
    zoneLayersRef.current = [];

    zones.forEach((zone) => {
      const color = riskColor(zone.risk_score_72h, theme);
      const polygon = L.polygon(toLatLngs(zone.geom), {
        color,
        weight: 1.6,
        opacity: 0.95,
        fillColor: color,
        fillOpacity: 0.26,
      }).addTo(map);

      polygon.on("mouseover", () => polygon.setStyle({ fillOpacity: 0.42, weight: 2.4 }));
      polygon.on("mouseout", () => polygon.setStyle({ fillOpacity: 0.26, weight: 1.6 }));
      polygon.on("click", () => onSelectZone?.(zone.zone_id));

      polygon.bindTooltip(`${zone.display_code ?? zone.zone_id} · ${zone.name}`, {
        direction: "top",
        sticky: true,
      });
      polygon.bindPopup(
        `<b>${zone.name}</b>${zone.display_code ?? ""}<br>` +
          `${zone.hazard_types.join(", ")}<br>` +
          `${zone.population.toLocaleString("en-IN")} residents<br>` +
          `Confidence: ${zone.data_confidence}` +
          (zone.risk_score_72h !== null ? `<br>72h risk: ${Math.round(zone.risk_score_72h * 100)}` : ""),
      );

      zoneLayersRef.current.push(polygon);
    });

    if (zones.length > 0) {
      const bounds = L.latLngBounds(zones.flatMap((z) => toLatLngs(z.geom)));
      map.fitBounds(bounds.pad(0.2));
    }
  }, [zones, theme, fallback, onSelectZone]);

  if (fallback) {
    return (
      <div style={{ padding: 16 }}>
        <p style={{ fontSize: 11, opacity: 0.7 }}>Basemap unavailable — zone data shown as list.</p>
        <ZoneListFallback zones={zones} theme={theme} />
      </div>
    );
  }

  return (
    <div style={{ position: "relative", height: "100%", minHeight: 420 }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
      <SampleDataBadge />
    </div>
  );
}

function ZoneListFallback({ zones, theme }: { zones: Zone[]; theme: Theme }) {
  return (
    <div style={{ border: "1px solid #1d2a45", borderRadius: 6, overflow: "hidden" }}>
      {zones.map((z) => (
        <div
          key={z.zone_id}
          style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 14px", borderBottom: "1px solid #1d2a45" }}
        >
          <span style={{ width: 10, height: 10, borderRadius: 2, background: riskColor(z.risk_score_72h, theme) }} />
          <span style={{ width: 64, fontFamily: "monospace", fontSize: 11 }}>{z.display_code}</span>
          <span style={{ flex: 1 }}>{z.name}</span>
          <span style={{ fontSize: 11, opacity: 0.7 }}>{z.hazard_types.join(", ")}</span>
        </div>
      ))}
    </div>
  );
}

// rule 6 — sample/seeded data is never shown without this marker.
function SampleDataBadge() {
  return (
    <div
      style={{
        position: "absolute",
        left: 10,
        bottom: 10,
        zIndex: 500,
        fontFamily: "monospace",
        fontSize: 10,
        letterSpacing: "0.04em",
        padding: "4px 8px",
        borderRadius: 3,
        background: "rgba(184,12,9,0.85)",
        color: "#fff",
      }}
    >
      SAMPLE DATA
    </div>
  );
}
