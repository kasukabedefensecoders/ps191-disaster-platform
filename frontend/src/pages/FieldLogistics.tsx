import { useEffect, useMemo, useState } from "react";

import { SampleDataBadge, TierBadge } from "../components/badges";
import {
  fetchRelocations,
  fetchShelters,
  fetchZoneHouseholds,
  fetchZones,
  updateRelocationStatus,
  type HouseholdRanked,
  type RelocationRecord,
  type Shelter,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const STATUS_META: Record<RelocationRecord["status"], { dot: string; label: string; next: string | null; action: string | null }> = {
  assigned: { dot: "var(--sev3)", label: "ASSIGNED · waiting for pickup", next: "in_transit", action: "Mark as In Transit" },
  in_transit: { dot: "var(--sev3)", label: "IN TRANSIT", next: "arrived", action: "Confirm Arrival" },
  arrived: { dot: "var(--sev5)", label: "ARRIVED · delivery complete", next: null, action: null },
};

/** Change 3 (Option B): the field-officer-facing counterpart to Logistics
 * Tracker's SDMA view. Same /relocations + PATCH /relocations/{id}/status
 * calls Relocations.tsx uses — the backend's own RLS (migration 0003,
 * household -> zone -> user_zone_assignments) is what actually limits a
 * field_officer to their assigned zones' relocations, so this page adds no
 * filtering of its own beyond that. Household/shelter display codes are
 * resolved client-side from the same RLS-scoped zone list Household
 * Assessment already fetches — there's no bulk household-lookup endpoint,
 * and one isn't worth adding just to avoid two more GETs a field officer's
 * own small zone roster makes cheap. */
export default function FieldLogistics() {
  const { token, user } = useAuth();
  const [records, setRecords] = useState<RelocationRecord[] | null>(null);
  const [households, setHouseholds] = useState<Record<string, HouseholdRanked>>({});
  const [shelters, setShelters] = useState<Record<string, Shelter>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const canAct = user?.role === "sdma_official" || user?.role === "field_officer";

  const load = () => {
    if (!token) return;
    fetchRelocations(token)
      .then((r) => setRecords(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);

  useEffect(() => {
    if (!token) return;
    fetchShelters(token)
      .then((r) => setShelters(Object.fromEntries(r.items.map((s) => [s.shelter_id, s]))))
      .catch(() => {});
    fetchZones(token)
      .then(async (r) => {
        const entries = await Promise.all(
          r.items.map(async (z) => (await fetchZoneHouseholds(token, z.zone_id).catch(() => ({ items: [] }))).items),
        );
        setHouseholds(Object.fromEntries(entries.flat().map((h) => [h.household_id, h])));
      })
      .catch(() => {});
  }, [token]);

  const sorted = useMemo(() => {
    if (!records) return null;
    const order: Record<string, number> = { assigned: 0, in_transit: 1, arrived: 2 };
    return [...records].sort((a, b) => order[a.status] - order[b.status]);
  }, [records]);

  const advance = async (record: RelocationRecord) => {
    const next = STATUS_META[record.status].next;
    if (!token || !next) return;
    setBusyId(record.record_id);
    try {
      await updateRelocationStatus(token, record.record_id, next);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!sorted) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading field updates…</p>;

  return (
    <div style={{ padding: 18, maxWidth: 720 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <h2 style={{ fontSize: 18 }}>Field officer logistics</h2>
        <SampleDataBadge />
      </div>
      <p style={{ font: "400 12px/1.5 var(--font-interface)", color: "var(--ink3)", marginBottom: 16 }}>
        Relocations assigned to you. Update status as you move households — the logistics tracker and dashboard update immediately.
      </p>

      {sorted.length === 0 && <p style={{ fontSize: 13, color: "var(--ink3)" }}>No relocations assigned right now.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sorted.map((r) => {
          const meta = STATUS_META[r.status];
          const household = households[r.household_id];
          const shelter = shelters[r.shelter_id];
          return (
            <div key={r.record_id} style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <span style={{ width: 9, height: 9, borderRadius: "50%", background: meta.dot, marginTop: 4, flex: "none" }} />
                  <div>
                    <div style={{ font: "600 13px/1.3 var(--font-data)", color: "var(--ink)" }}>
                      {household?.display_code ?? "HH-?"} → {shelter?.display_code ?? "SH-?"} {shelter?.name ?? ""}
                    </div>
                    <div style={{ font: "500 10.5px/1.6 var(--font-data)", color: "var(--ink3)", letterSpacing: "0.03em" }}>{meta.label}</div>
                    {household && (
                      <div style={{ font: "400 11px/1.5 var(--font-data)", color: "var(--ink4)", marginTop: 3 }}>
                        Population {household.population_count} ({household.children_count} children, {household.elderly_count} elderly)
                      </div>
                    )}
                  </div>
                </div>
                <TierBadge tier={r.priority_tier} />
              </div>
              {meta.action && canAct && (
                <div style={{ marginTop: 10 }}>
                  <button
                    onClick={() => advance(r)}
                    disabled={busyId === r.record_id}
                    className="ps-btn-primary"
                    style={{
                      padding: "7px 14px",
                      borderRadius: 4,
                      border: "1px solid var(--accent)",
                      background: "var(--accent)",
                      color: "var(--on-accent)",
                      font: "600 12px/1 var(--font-interface)",
                      cursor: busyId === r.record_id ? "default" : "pointer",
                    }}
                  >
                    {busyId === r.record_id ? "Updating…" : meta.action}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
