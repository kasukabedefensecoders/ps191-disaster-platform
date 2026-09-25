import { useEffect, useState } from "react";

import { SampleDataBadge, TierBadge } from "../components/badges";
import VehicleRouteModal from "../components/VehicleRouteModal";
import {
  fetchRelocationsByVehicle,
  fetchShelters,
  fetchZoneHouseholds,
  fetchZones,
  updateRelocationStatus,
  type HouseholdRanked,
  type RelocationRecord,
  type Shelter,
  type VehicleGroup,
  type Zone,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const STATUS_META: Record<RelocationRecord["status"], { label: string; color: string; next: RelocationRecord["status"] | null; action: string | null }> = {
  assigned: { label: "ASSIGNED", color: "var(--sev3)", next: "in_transit", action: "Mark In Transit" },
  in_transit: { label: "IN TRANSIT", color: "var(--sev3)", next: "arrived", action: "Mark Arrived" },
  arrived: { label: "ARRIVED", color: "var(--sev5)", next: null, action: null },
};

function occupancyPct(occupancy: number, capacity: number | null): number {
  if (!capacity) return 0;
  return Math.min(100, Math.round((occupancy / capacity) * 100));
}

function occupancyColor(pct: number): string {
  if (pct > 95) return "var(--sev1)";
  if (pct >= 80) return "var(--sev3)";
  return "var(--sev5)";
}

function fmtTime(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

// vehicle_type is free text (docs/BACKEND-SCHEMA.md §5.7) — matched
// case-insensitively so seed data casing changes don't silently fall back
// to the "no vehicle assigned" icon.
function vehicleIcon(vehicleType: string | null): string {
  switch (vehicleType?.toLowerCase()) {
    case "bus":
      return "🚌";
    case "truck":
      return "🚚";
    default:
      return "❓";
  }
}

// A vehicle's pickup point for "View Route" — the households on one
// vehicle can come from several zones at once (demo_seed.py's VEHICLE_PLAN
// deliberately consolidates a few, e.g. BUS-02 carries one ZN-01 and one
// ZN-02 household to SH-02), so there's no single zone this can always
// point at. Every household in the same zone shares that zone's own
// seeded point (app/seed.py's HOUSEHOLDS all use ZONE_CENTROIDS), so this
// dedupes by zone and averages the distinct zone points — a genuine
// "roughly where this run is collecting from" location to hand to OSRM,
// not a fabricated single-household address.
function pickupPointForGroup(
  group: VehicleGroup,
  householdsById: Record<string, HouseholdRanked>,
  zonesById: Record<string, Zone>,
): { point: [number, number]; label: string } | null {
  const zonePoints = new Map<string, [number, number]>();
  for (const h of group.households) {
    const hh = householdsById[h.household_id];
    if (hh && !zonePoints.has(hh.zone_id)) zonePoints.set(hh.zone_id, hh.geom.coordinates);
  }
  if (zonePoints.size === 0) return null;

  const zoneIds = [...zonePoints.keys()];
  const points = [...zonePoints.values()];
  const avgLon = points.reduce((s, p) => s + p[0], 0) / points.length;
  const avgLat = points.reduce((s, p) => s + p[1], 0) / points.length;

  const zoneLabels = zoneIds.map((zid) => zonesById[zid]?.display_code ?? zid);
  const label =
    zoneIds.length === 1
      ? `${zoneLabels[0]} · ${zonesById[zoneIds[0]]?.name ?? ""} (pickup)`.trim()
      : `${zoneLabels.join(", ")} (pickup — ${group.households.length} households)`;

  return { point: [avgLon, avgLat], label };
}

/** Change 3: the Logistics Tracker's bus-consolidation cards — several
 * households sharing one vehicle, grouped server-side by GET /relocations/
 * by-vehicle (services/relocations.py's group_relocations_by_vehicle).
 * Collapsed by default; expanding a card is the only way to see its
 * households and the only place action buttons appear, so a district with
 * many active runs doesn't turn into a wall of buttons. */
export default function Relocations() {
  const { token, user } = useAuth();
  const [groups, setGroups] = useState<VehicleGroup[] | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [householdsById, setHouseholdsById] = useState<Record<string, HouseholdRanked>>({});
  const [zonesById, setZonesById] = useState<Record<string, Zone>>({});
  const [sheltersById, setSheltersById] = useState<Record<string, Shelter>>({});
  const [viewingRouteFor, setViewingRouteFor] = useState<VehicleGroup | null>(null);

  const load = () => {
    if (!token) return;
    fetchRelocationsByVehicle(token)
      .then((r) => setGroups(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);

  // "View Route" needs each household's own zone_id/geom (not returned by
  // /relocations/by-vehicle at all) and each shelter's geom (that endpoint
  // only sends display_code/name) — fetched once, same pattern
  // FieldLogistics.tsx already uses for the same household-lookup need.
  useEffect(() => {
    if (!token) return;
    fetchShelters(token)
      .then((r) => setSheltersById(Object.fromEntries(r.items.map((s) => [s.shelter_id, s]))))
      .catch(() => {});
    fetchZones(token)
      .then(async (r) => {
        setZonesById(Object.fromEntries(r.items.map((z) => [z.zone_id, z])));
        const entries = await Promise.all(
          r.items.map(async (z) => (await fetchZoneHouseholds(token, z.zone_id).catch(() => ({ items: [] }))).items),
        );
        setHouseholdsById(Object.fromEntries(entries.flat().map((h) => [h.household_id, h])));
      })
      .catch(() => {});
  }, [token]);

  const toggle = (key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const advanceBus = async (group: VehicleGroup) => {
    const meta = STATUS_META[group.status];
    if (!token || !meta.next) return;
    const key = group.vehicle_id ?? "unassigned";
    // Only households still one step behind the bus's next status move —
    // a card is a single collapsed action, but the households on it can
    // individually be at different steps if someone updated one directly
    // (e.g. from Field Officer Logistics) before this bulk click.
    const targets = group.households.filter((h) => STATUS_META[h.status].next === meta.next);
    if (targets.length === 0) return;
    setBusyKey(key);
    setError(null);
    try {
      for (const household of targets) {
        await updateRelocationStatus(token, household.record_id, meta.next);
      }
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyKey(null);
    }
  };

  if (!groups && error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!groups) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading logistics tracker…</p>;

  return (
    <div data-reveal="" style={{ padding: 16, maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ fontSize: 18 }}>Logistics tracker</h2>
        <SampleDataBadge />
      </div>
      {error && <p style={{ color: "var(--sev1)", fontSize: 12, marginBottom: 10 }}>{error}</p>}
      {groups.length === 0 && <p style={{ color: "var(--ink3)", fontSize: 13 }}>No relocation decisions yet.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {groups.map((group) => {
          const key = group.vehicle_id ?? "unassigned";
          const isExpanded = expanded.has(key);
          const meta = STATUS_META[group.status];
          const pct = occupancyPct(group.current_occupancy, group.capacity);
          const title = group.vehicle_display_code ?? "Unassigned households";
          const subtitle = group.route_label ? ` (${group.route_label})` : "";

          return (
            <div key={key} style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
              <button
                onClick={() => toggle(key)}
                className="ps-row-hover"
                style={{ width: "100%", textAlign: "left", background: "transparent", border: 0, cursor: "pointer", padding: "12px 14px" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 16 }}>{vehicleIcon(group.vehicle_type)}</span>
                    <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>
                      {title}
                      {subtitle}
                    </span>
                    <span style={{ font: "400 12px/1 var(--font-interface)", color: "var(--ink3)" }}>
                      — {group.households.length} household{group.households.length === 1 ? "" : "s"}
                      {group.capacity !== null && `, ${group.current_occupancy}/${group.capacity} capacity`}
                    </span>
                  </div>
                  <span style={{ font: "500 9px/1 var(--font-data)", color: "var(--ink4)" }}>{isExpanded ? "▲ COLLAPSE" : "▼ EXPAND"}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, font: "600 10.5px/1 var(--font-data)", letterSpacing: "0.04em", color: meta.color }}>
                    {group.status === "in_transit" && (
                      <span style={{ width: 5, height: 5, borderRadius: "50%", background: meta.color, animation: "pulseDot 2s ease-in-out infinite" }} />
                    )}
                    {meta.label}
                  </span>
                  {group.departed_at && (
                    <span style={{ font: "400 11px/1 var(--font-data)", color: "var(--ink4)" }}>Departed {fmtTime(group.departed_at)}</span>
                  )}
                  {group.estimated_arrival && group.status === "in_transit" && (
                    <span style={{ font: "400 11px/1 var(--font-data)", color: "var(--ink4)" }}>ETA {fmtTime(group.estimated_arrival)}</span>
                  )}
                  {group.status === "assigned" && <span style={{ font: "400 11px/1 var(--font-data)", color: "var(--ink4)" }}>Waiting for pickup</span>}
                </div>
                {group.capacity !== null && (
                  <div style={{ marginTop: 8, height: 4, borderRadius: 2, background: "var(--track)", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${pct}%`, background: occupancyColor(pct) }} />
                  </div>
                )}
              </button>

              {isExpanded && (
                <div style={{ borderTop: "1px solid var(--border)", padding: "12px 14px" }}>
                  {group.capacity !== null && (
                    <div style={{ font: "400 11.5px/1.5 var(--font-interface)", color: "var(--ink3)", marginBottom: 10 }}>
                      Capacity: {group.current_occupancy}/{group.capacity} ({pct}% full)
                    </div>
                  )}
                  <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 8 }}>
                    Households on this {group.vehicle_id ? "vehicle" : "record"}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                    {group.households.map((h) => (
                      <div key={h.record_id} style={{ background: "var(--panel2)", border: "1px solid var(--border-soft)", borderRadius: 5, padding: 10 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ font: "600 12.5px/1 var(--font-data)", color: "var(--ink)" }}>
                            {h.household_display_code} → {h.shelter_display_code} {h.shelter_name}
                          </span>
                          <TierBadge tier={h.priority_tier} />
                        </div>
                        <div style={{ font: "400 11.5px/1.5 var(--font-interface)", color: "var(--ink3)", marginTop: 4 }}>
                          Population: {h.population_count} ({h.children_count} children, {h.elderly_count} elderly, {h.assistance_needs_count} assistance)
                        </div>
                        <div style={{ font: "400 10.5px/1.4 var(--font-data)", color: "var(--ink4)", marginTop: 2 }}>
                          {h.arrived_at
                            ? `Arrived ${fmtTime(h.arrived_at)}`
                            : h.boarded_at
                              ? `Boarded ${fmtTime(h.boarded_at)}`
                              : "Waiting for pickup"}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {meta.action && user?.role === "sdma_official" && (
                      <button onClick={() => advanceBus(group)} disabled={busyKey === key} className="ps-btn-primary" style={actionButtonStyle}>
                        {busyKey === key ? "Updating…" : meta.action}
                      </button>
                    )}
                    <button
                      onClick={() => setViewingRouteFor(group)}
                      disabled={!pickupPointForGroup(group, householdsById, zonesById) || !sheltersById[group.households[0]?.shelter_id ?? ""]}
                      title={
                        pickupPointForGroup(group, householdsById, zonesById) && sheltersById[group.households[0]?.shelter_id ?? ""]
                          ? undefined
                          : "Loading route data…"
                      }
                      className="ps-btn-outline"
                      style={outlineButtonStyle}
                    >
                      View Route
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {viewingRouteFor && (() => {
        const pickup = pickupPointForGroup(viewingRouteFor, householdsById, zonesById);
        const shelterId = viewingRouteFor.households[0]?.shelter_id;
        const shelter = shelterId ? sheltersById[shelterId] : undefined;
        // The button that opens this is disabled until both resolve, so
        // this guard is only ever hit if data changed out from under an
        // already-open modal (e.g. a reset) — closing quietly beats
        // rendering a route to [0, 0].
        if (!pickup || !shelter) return null;

        const title = `${viewingRouteFor.vehicle_display_code ?? "Unassigned"}${viewingRouteFor.route_label ? ` (${viewingRouteFor.route_label})` : ""}`;

        return (
          <VehicleRouteModal
            key={viewingRouteFor.vehicle_id ?? "unassigned"}
            title={title}
            originLabel={pickup.label}
            destLabel={`${shelter.display_code} · ${shelter.name}`}
            origin={pickup.point}
            dest={shelter.geom.coordinates}
            onClose={() => setViewingRouteFor(null)}
          />
        );
      })()}
    </div>
  );
}

const actionButtonStyle = {
  padding: "7px 14px",
  borderRadius: 4,
  border: "1px solid var(--accent)",
  background: "var(--accent)",
  color: "var(--on-accent)",
  font: "600 12px/1 var(--font-interface)",
  cursor: "pointer",
} as const;

const outlineButtonStyle = {
  padding: "7px 14px",
  borderRadius: 4,
  border: "1px solid var(--border2)",
  background: "transparent",
  color: "var(--ink2)",
  font: "600 12px/1 var(--font-interface)",
  cursor: "pointer",
} as const;
