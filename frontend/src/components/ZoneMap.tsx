import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";

import type { Zone } from "../lib/api";
import { riskColor, type Theme } from "../lib/riskColor";

/**
 * Leaflet setup ported from PROTOTYPE/dima-hasao-map.html per CLAUDE.md,
 * with two changes from the prototype's own OSM -> Esri chain, both forced
 * by the same failure mode: a "free" tile provider quietly starting to
 * require an API key and baking an "API KEY REQUIRED" watermark into the
 * tile image itself, rather than failing the request — a load Leaflet's
 * own error/tileerror events can't detect (the request succeeds; it's just
 * visually broken), so no amount of retry logic recovers from it, and it
 * only shows up by actually loading the tile and looking at it. Esri's
 * "Canvas" World_Light/Dark_Gray_Base services (the prototype's original
 * fallback) hit this first; CartoDB's basemaps.cartocdn.com — brought in
 * specifically to replace Esri for the same reason — hit it too, some time
 * after that fix shipped (confirmed live again). Rather than chase a third
 * "free real dark tiles" provider that can pull the same move, the fallback
 * tier is now a second, independently-run OSM mirror (the standard
 * tile.openstreetmap.org, distinct infrastructure from the .fr mirror
 * that's tier one) — always-light tiles like tier one, inverted for dark
 * theme by the same CSS filter both tiers now share unconditionally.
 */

type TileKind = "osm" | "osm2";

const OSM_URL = "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png";
const OSM2_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const NEXT_TILE_KIND: Record<TileKind, TileKind | null> = { osm: "osm2", osm2: null };
const TILE_TIMEOUT_MS = 3500;

function toLatLngs(geom: Zone["geom"]): L.LatLngExpression[] {
  // GeoJSON is [lon, lat]; Leaflet wants [lat, lon]. Only the outer ring —
  // zones.geom is a plain Polygon (Backend Schema §5.3), never a hole.
  return geom.coordinates[0].map(([lon, lat]) => [lat, lon] as L.LatLngExpression);
}

interface ZoneMapProps {
  zones: Zone[];
  theme?: Theme;
  onSelectZone?: (zoneId: string) => void;
  /** Shown alongside the "basemap unavailable" fallback when there are no
   * zones to list either (e.g. the public landing page's hero preview,
   * which never receives real zone data pre-auth). */
  emptyFallbackNote?: string;
}

export default function ZoneMap({ zones, theme = "dark", onSelectZone, emptyFallbackNote }: ZoneMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const zoneLayersRef = useRef<L.Polygon[]>([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = L.map(containerRef.current, { zoomControl: true, attributionControl: true });
    mapRef.current = map;

    // React 18 StrictMode mounts, cleans up, and remounts every effect once
    // in dev — map.remove() runs between the two. Without this guard, the
    // first mount's fallback timer fires after that cleanup and calls
    // .addTo(map) on an already-torn-down Leaflet map (whose container was
    // ripped out from under it), crashing on a null appendChild. Caught by
    // actually loading the page, not by the type-checker or the test suite.
    let live = true;
    let tileErrorCount = 0;
    let tileLoadCount = 0;

    const TILE_URL: Record<TileKind, string> = { osm: OSM_URL, osm2: OSM2_URL };

    const setTileLayer = (kind: TileKind) => {
      if (!live) return;
      if (tileLayerRef.current) map.removeLayer(tileLayerRef.current);
      // Both tiers are always-light OSM tiles — tokens.css unconditionally
      // inverts .leaflet-tile-pane for dark theme (PROTOTYPE/
      // dima-hasao-map.html's own body[data-theme="dark"]
      // .leaflet-tile-pane{filter:invert(1)...} trick, scoped per-map-
      // instance instead of globally), so no data-tile-kind branching is
      // needed here any more — CSS handles both tiers identically, and a
      // theme toggle never has to touch this Leaflet instance at all.
      const layer = L.tileLayer(TILE_URL[kind], {
        attribution: "© OpenStreetMap contributors",
        maxZoom: 18,
        subdomains: "abc",
      });
      layer.addTo(map);
      tileLayerRef.current = layer;

      tileLoadCount = 0;
      tileErrorCount = 0;
      layer.on("load", () => {
        tileLoadCount++;
        setLoaded(true);
      });
      layer.on("tileerror", () => {
        tileErrorCount++;
        if (tileErrorCount >= 6) escalate(kind);
      });
      setTimeout(() => {
        if (live && tileLoadCount === 0) escalate(kind);
      }, TILE_TIMEOUT_MS);
    };

    const escalate = (fromKind: TileKind) => {
      if (!live) return;
      const next = NEXT_TILE_KIND[fromKind];
      if (next) {
        setTileLayer(next);
      } else {
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
    // Tile URLs no longer depend on theme (see the comment above) — the map
    // is created once on mount and never torn down/rebuilt on a theme
    // toggle; CSS alone handles the dark-mode look.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    } else {
      // Dima Hasao district centre (Haflong) — real coordinates, matching
      // the seeded zones' own centroids, not a generic India view.
      map.setView([25.17, 93.02], 10);
    }
  }, [zones, theme, fallback, onSelectZone]);

  if (fallback) {
    return (
      <div style={{ padding: 16 }}>
        <p style={{ fontSize: 11, opacity: 0.7 }}>Basemap unavailable — zone data shown as list.</p>
        {zones.length > 0 ? <ZoneListFallback zones={zones} theme={theme} /> : emptyFallbackNote && <p style={{ fontSize: 11, color: "var(--ink4)" }}>{emptyFallbackNote}</p>}
      </div>
    );
  }

  return (
    <div style={{ position: "relative", height: "100%", minHeight: 420 }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0, background: "var(--bg2)" }} />
      {!loaded && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 400,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
            background: "var(--bg2)",
          }}
        >
          <span style={{ fontFamily: "var(--font-data)", fontSize: 11, color: "var(--ink4)", letterSpacing: "0.06em" }}>
            LOADING BASEMAP…
          </span>
        </div>
      )}
      <SampleDataBadge />
    </div>
  );
}

function ZoneListFallback({ zones, theme }: { zones: Zone[]; theme: Theme }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
      {zones.map((z) => (
        <div
          key={z.zone_id}
          style={{ display: "flex", gap: 12, alignItems: "center", padding: "10px 14px", borderBottom: "1px solid var(--border-soft)" }}
        >
          <span style={{ width: 10, height: 10, borderRadius: 2, background: riskColor(z.risk_score_72h, theme) }} />
          <span style={{ width: 64, fontFamily: "var(--font-data)", fontSize: 11 }}>{z.display_code}</span>
          <span style={{ flex: 1, fontFamily: "var(--font-interface)" }}>{z.name}</span>
          <span style={{ fontSize: 11, opacity: 0.7 }}>{z.hazard_types.join(", ")}</span>
        </div>
      ))}
    </div>
  );
}

// PROTOTYPE/PS191 Platform.dc.html line 97's hero-map caption chip — a
// pulsing live-dot + mono label, not a filled red pill (rule 6 — sample/
// seeded data is never shown without this marker).
function SampleDataBadge() {
  return (
    <div
      style={{
        position: "absolute",
        left: 12,
        bottom: 12,
        zIndex: 500,
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 8px",
        borderRadius: 3,
        background: "var(--panel)",
        border: "1px solid var(--border2)",
        fontFamily: "var(--font-data)",
        fontWeight: 500,
        fontSize: 10,
        color: "var(--ink3)",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--sev5)", animation: "pulseDot 2s ease-in-out infinite" }} />
      LIVE HAZARD ZONING · SAMPLE DATA
    </div>
  );
}
