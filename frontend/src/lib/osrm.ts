import type { GeoJSONLineString } from "./api";

/**
 * Client-side call to OSRM's free public demo server — no key, and it
 * already covers OSM's global road network (including Assam), so this is
 * a genuine road-following route, not another synthetic straight line.
 * TRD §11's "no OSRM instance" gap was about self-hosting the engine for
 * server-side shelter matching; this sidesteps that entirely by calling
 * the public demo API directly from the browser, which is exactly what
 * it's there for. Never call this from the backend — it's a shared public
 * resource, rate-limited per caller, and has no SLA.
 */
const OSRM_BASE = "https://router.project-osrm.org/route/v1/driving";
const OSRM_TIMEOUT_MS = 6000;

export interface OsrmRoute {
  path: GeoJSONLineString;
  distance_km: number;
  duration_minutes: number;
}

/** [lon, lat] in, [lon, lat] out — matches this app's GeoJSON convention
 * throughout (not [lat, lon], which only Leaflet itself uses). Returns
 * null (after a console.warn) on any failure — timeout, network, rate
 * limit, or a malformed/empty response — so callers can fall back to
 * whatever straight-line or pre-fetched geometry they already have rather
 * than breaking the page. */
export async function fetchOsrmRoute(origin: [number, number], dest: [number, number]): Promise<OsrmRoute | null> {
  const url = `${OSRM_BASE}/${origin[0]},${origin[1]};${dest[0]},${dest[1]}?overview=full&geometries=geojson`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), OSRM_TIMEOUT_MS);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`OSRM responded ${res.status}`);
    const body = await res.json();
    const route = body?.routes?.[0];
    const coordinates = route?.geometry?.coordinates;
    if (!Array.isArray(coordinates) || coordinates.length < 2) throw new Error("OSRM returned no usable route geometry");
    return {
      path: { type: "LineString", coordinates },
      distance_km: route.distance / 1000,
      duration_minutes: route.duration / 60,
    };
  } catch (err) {
    console.warn("OSRM route fetch failed — falling back to the straight-line/pre-fetched route instead.", err);
    return null;
  } finally {
    clearTimeout(timeout);
  }
}
