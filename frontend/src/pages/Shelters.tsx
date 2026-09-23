import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import FactorsPanel from "../components/FactorsPanel";
import { SampleDataBadge, TierBadge } from "../components/badges";
import {
  createRelocation,
  createShelter,
  fetchShelterMatches,
  fetchShelters,
  fetchVehicles,
  type HouseholdRanked,
  type RelocationRecord,
  type Shelter,
  type ShelterMatch,
  type ShelterStatus,
  type Vehicle,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { CANONICAL_FACILITIES, EXTRA_FACILITIES, STATUS_META, STATUS_OPTIONS, facilityTags, occupancyColor, occupancyPct } from "../lib/shelterDisplay";

export default function Shelters() {
  const { token, user } = useAuth();
  const location = useLocation();
  const [shelters, setShelters] = useState<Shelter[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<Date | null>(null);
  const [allocationTarget, setAllocationTarget] = useState<HouseholdRanked | null>(
    (location.state as { household?: HouseholdRanked } | null)?.household ?? null,
  );

  const canRegister = user?.role === "sdma_official";

  const load = () => {
    if (!token) return;
    fetchShelters(token)
      .then((r) => {
        setShelters(r.items);
        setLastLoadedAt(new Date());
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);

  const summary = useMemo(() => {
    if (!shelters) return null;
    const capacity = shelters.reduce((sum, s) => sum + s.max_capacity, 0);
    const occupied = shelters.reduce((sum, s) => sum + s.current_occupancy, 0);
    const critical = shelters.filter((s) => occupancyPct(s) > 95);
    const shortages = new Map<string, number>();
    for (const s of shelters) {
      for (const need of s.needs) shortages.set(need, (shortages.get(need) ?? 0) + 1);
    }
    const lastUpdated = shelters.reduce<Date | null>((latest, s) => {
      const t = new Date(s.last_updated_at ?? s.updated_at);
      return !latest || t > latest ? t : latest;
    }, null);
    return {
      count: shelters.length,
      capacity,
      occupied,
      pct: capacity > 0 ? Math.round((occupied / capacity) * 100) : 0,
      critical,
      shortages: [...shortages.entries()].sort((a, b) => b[1] - a[1]),
      lastUpdated,
    };
  }, [shelters]);

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load shelters: {error}</p>;
  if (!shelters || !summary) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading shelters…</p>;

  return (
    <div style={{ padding: 18, maxWidth: 1240 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ fontSize: 18, marginBottom: 4 }}>Shelter registration &amp; management</h2>
          <div style={{ font: "400 11.5px/1.5 var(--font-interface)", color: "var(--ink3)" }}>
            Occupancy, facilities, needs and status below are reported by each shelter's own officer from their
            shelter dashboard (signed in separately, with their shelter's code) — read-only here.
          </div>
        </div>
        <SampleDataBadge />
      </div>

      {allocationTarget && canRegister && (
        <AllocationPanel
          token={token!}
          household={allocationTarget}
          onClose={() => setAllocationTarget(null)}
          onAllocated={load}
        />
      )}

      {canRegister && (
        <RegistrationForm
          token={token!}
          districtId={user!.district_id}
          existingCodes={shelters.map((s) => s.display_code ?? "")}
          onRegistered={load}
        />
      )}

      <div style={{ display: "flex", gap: 14, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: "2 1 560px", minWidth: 0, background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
          <div style={{ display: "flex", padding: "10px 16px", borderBottom: "1px solid var(--border)", gap: 8 }}>
            {["Shelter", "Occupancy", "Facilities", "Needs", "Status"].map((h) => (
              <span
                key={h}
                style={{
                  flex: h === "Shelter" ? 2 : h === "Facilities" || h === "Needs" ? 1.3 : 1,
                  font: "500 10px/1 var(--font-data)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--ink4)",
                }}
              >
                {h}
              </span>
            ))}
          </div>
          {shelters.map((s) => (
            <ShelterRow key={s.shelter_id} shelter={s} />
          ))}
        </div>

        <div style={{ flex: "1 1 280px", minWidth: 260, display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel title="Shelter headroom">
            <div style={{ padding: "12px 16px" }}>
              <div style={{ font: "400 12.5px/1.5 var(--font-interface)", color: "var(--ink2)" }}>
                {summary.count} shelter{summary.count === 1 ? "" : "s"}, {summary.occupied.toLocaleString("en-IN")}/
                {summary.capacity.toLocaleString("en-IN")} capacity ({summary.pct}%)
              </div>
              <div style={{ marginTop: 8, height: 5, borderRadius: 3, background: "var(--track)", overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${summary.pct}%`, background: occupancyColor(summary.pct) }} />
              </div>
            </div>
          </Panel>

          <Panel title="Critical needs">
            {summary.critical.length === 0 ? (
              <p style={{ padding: "12px 16px", fontSize: 12, color: "var(--ink3)" }}>No shelter above 95% capacity.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column" }}>
                {summary.critical.map((s) => (
                  <div key={s.shelter_id} style={{ display: "flex", justifyContent: "space-between", padding: "10px 16px", borderBottom: "1px solid var(--border-soft)" }}>
                    <span style={{ font: "500 12px/1.3 var(--font-interface)", color: "var(--alert-ink)" }}>
                      {s.display_code} · {s.name}
                    </span>
                    <span style={{ font: "600 12px/1 var(--font-data)", color: "var(--sev1)" }}>{occupancyPct(s)}%</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Current shortages">
            {summary.shortages.length === 0 ? (
              <p style={{ padding: "12px 16px", fontSize: 12, color: "var(--ink3)" }}>No urgent needs flagged.</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "12px 16px" }}>
                {summary.shortages.map(([need, count]) => (
                  <span key={need} style={needChipStyle}>
                    {need} × {count}
                  </span>
                ))}
              </div>
            )}
          </Panel>

          <div style={{ font: "400 10.5px/1.5 var(--font-data)", color: "var(--ink4)" }}>
            Last updated {summary.lastUpdated ? summary.lastUpdated.toLocaleString("en-IN") : "—"}
            {lastLoadedAt && <> · list refreshed {lastLoadedAt.toLocaleTimeString("en-IN")}</>}
          </div>
        </div>
      </div>
    </div>
  );
}

const MEDALS = ["🥇", "🥈", "🥉"];

/** Change 2: the allocation workflow. Arrives here via a household's
 * "Allocate to shelter →" button on Household Assessment (React Router
 * `state`, not a query param, since the recommendation itself needs the
 * household's full scoring — see HouseholdAssessment.tsx). Ranks shelters
 * by the real /households/{id}/shelter-matches endpoint (Phase 5's
 * matchScore()) and renders exactly the factors[] it returns — rule 1: this
 * never recomputes or invents a score, including the "children/elderly
 * facility" ticks the original mockup imagined but the schema doesn't
 * model (shelters only carry water/medical/toilets/power + capacity). */
function AllocationPanel({
  token,
  household,
  onClose,
  onAllocated,
}: {
  token: string;
  household: HouseholdRanked;
  onClose: () => void;
  onAllocated: () => void;
}) {
  const navigate = useNavigate();
  const [matches, setMatches] = useState<ShelterMatch[] | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [allocated, setAllocated] = useState<RelocationRecord | null>(null);

  useEffect(() => {
    setMatches(null);
    setAllocated(null);
    setError(null);
    fetchShelterMatches(token, household.household_id)
      .then((r) => setMatches(r.items.slice(0, 3)))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    fetchVehicles(token).then(setVehicles).catch(() => setVehicles([]));
  }, [token, household.household_id]);

  const allocate = async (shelterId: string) => {
    setBusyId(shelterId);
    setError(null);
    try {
      const record = await createRelocation(token, { household_id: household.household_id, shelter_id: shelterId });
      setAllocated(record);
      onAllocated();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const assignedVehicle = allocated?.vehicle_id ? vehicles?.find((v) => v.vehicle_id === allocated.vehicle_id) : null;

  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--accent)", borderRadius: 6, padding: 16, marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <div style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 4 }}>
            Recommended shelters for {household.display_code}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ font: "400 12px/1.4 var(--font-interface)", color: "var(--ink2)" }}>
              {household.population_count} people · {household.children_count} children · {household.elderly_count} elderly ·{" "}
              {household.assistance_needs_count} need assistance
            </span>
            <TierBadge tier={household.priority_tier} />
          </div>
        </div>
        <button onClick={onClose} className="ps-icon-btn" style={{ background: "transparent", border: "none", color: "var(--ink4)", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>
          ✕
        </button>
      </div>

      {allocated && (
        <div style={{ padding: "11px 13px", borderRadius: 5, background: "var(--ok-bg)", border: "1px solid var(--ok-border)", font: "400 12px/1.6 var(--font-interface)", color: "var(--sev5-ink)", marginBottom: 12 }}>
          Allocated — <strong style={{ font: "600 13px/1 var(--font-data)" }}>{allocated.display_code}</strong> created,{" "}
          status <strong>{allocated.status}</strong>.{" "}
          {assignedVehicle ? (
            <>Vehicle auto-assigned: {assignedVehicle.vehicle_type} (capacity {assignedVehicle.capacity}).</>
          ) : (
            <>No vehicle currently available — pickup is unassigned until one frees up.</>
          )}{" "}
          <button
            onClick={() => navigate("/relocations")}
            style={{ border: "none", background: "transparent", color: "var(--sev5-ink)", textDecoration: "underline", cursor: "pointer", padding: 0, font: "600 12px/1 var(--font-interface)" }}
          >
            View in logistics tracker →
          </button>
        </div>
      )}

      {error && <div style={{ fontSize: 12, color: "var(--sev1)", marginBottom: 10 }}>{error}</div>}
      {!matches && !error && <p style={{ fontSize: 12, color: "var(--ink3)" }}>Ranking shelters…</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {matches?.map((m, i) => {
          const free = m.max_capacity - m.current_occupancy;
          return (
            <div key={m.shelter_id} style={{ background: "var(--panel2)", border: "1px solid var(--border2)", borderRadius: 5, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>
                    {MEDALS[i] ?? ""} {m.display_code} {m.name}
                  </span>
                  <div style={{ font: "400 11px/1.6 var(--font-data)", color: "var(--ink3)", marginTop: 4 }}>
                    Distance {m.distance_km} km · Free capacity {free}/{m.max_capacity} · Facilities: {facilityTags(m.facilities).join(", ") || "none"}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ font: "700 16px/1 var(--font-data)", color: "var(--sev2-ink)" }}>{Math.round(m.match_score * 100)}%</div>
                  <div style={{ font: "400 10px/1 var(--font-data)", color: "var(--ink4)" }}>match score</div>
                </div>
              </div>
              <details style={{ marginTop: 8 }}>
                <summary style={{ font: "500 11px/1 var(--font-interface)", color: "var(--ink3)", cursor: "pointer" }}>Why this score?</summary>
                <div style={{ marginTop: 8 }}>
                  <FactorsPanel factors={m.match_factors} />
                </div>
              </details>
              <div style={{ marginTop: 10 }}>
                <button
                  onClick={() => allocate(m.shelter_id)}
                  disabled={busyId !== null || allocated !== null || m.status === "closed" || m.status === "damaged"}
                  className="ps-btn-primary"
                  style={{
                    padding: "7px 14px",
                    borderRadius: 4,
                    border: "1px solid var(--accent)",
                    background: "var(--accent)",
                    color: "var(--on-accent)",
                    font: "600 12px/1 var(--font-interface)",
                    cursor: busyId !== null || allocated !== null ? "default" : "pointer",
                    opacity: allocated && allocated.shelter_id !== m.shelter_id ? 0.5 : 1,
                  }}
                >
                  {busyId === m.shelter_id ? "Allocating…" : `Allocate to ${m.display_code}`}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RegistrationForm({
  token,
  districtId,
  existingCodes,
  onRegistered,
}: {
  token: string;
  districtId: string | null;
  existingCodes: string[];
  onRegistered: () => void;
}) {
  const [name, setName] = useState("");
  const [lat, setLat] = useState("25.170");
  const [lng, setLng] = useState("93.020");
  const [capacity, setCapacity] = useState("100");
  const [canonical, setCanonical] = useState<Record<string, boolean>>({ power: false, water: false, medical: false, toilets: false });
  const [extras, setExtras] = useState<Record<string, boolean>>({ kitchen: false, blankets: false, "food storage": false });
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [status, setStatus] = useState<ShelterStatus>("active");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [registeredCode, setRegisteredCode] = useState<string | null>(null);

  const nextDisplayCode = useMemo(() => {
    let highest = 0;
    for (const code of existingCodes) {
      const match = /^SH-(\d+)$/.exec(code);
      if (match) highest = Math.max(highest, parseInt(match[1], 10));
    }
    return `SH-${String(highest + 1).padStart(2, "0")}`;
  }, [existingCodes]);

  const submit = async () => {
    if (!districtId) {
      setFormError("No district assigned to this account — cannot register a shelter.");
      return;
    }
    const capacityNum = parseInt(capacity, 10);
    const latNum = parseFloat(lat);
    const lngNum = parseFloat(lng);
    if (!name.trim()) {
      setFormError("Shelter name is required.");
      return;
    }
    if (!Number.isFinite(capacityNum) || capacityNum <= 0) {
      setFormError("Capacity must be a positive number.");
      return;
    }
    if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) {
      setFormError("Location must be valid latitude/longitude.");
      return;
    }
    setFormError(null);
    setRegisteredCode(null);
    setSubmitting(true);
    try {
      await createShelter(token, {
        display_code: nextDisplayCode,
        district_id: districtId,
        name: name.trim(),
        geom: { type: "Point", coordinates: [lngNum, latNum] },
        max_capacity: capacityNum,
        current_occupancy: 0,
        facilities: {
          ...canonical,
          other: Object.entries(extras)
            .filter(([, v]) => v)
            .map(([k]) => k),
        },
        status,
        contact_name: contactName.trim() || null,
        contact_phone: contactPhone.trim() || null,
        needs: [],
      });
      setName("");
      setContactName("");
      setContactPhone("");
      setCanonical({ power: false, water: false, medical: false, toilets: false });
      setExtras({ kitchen: false, blankets: false, "food storage": false });
      setStatus("active");
      setRegisteredCode(nextDisplayCode);
      onRegistered();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: 16, marginBottom: 16 }}>
      <div style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 12 }}>
        Register a new shelter · next ID {nextDisplayCode}
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
        <input placeholder="Shelter name" value={name} onChange={(e) => setName(e.target.value)} style={{ ...fieldStyle, flex: "2 1 220px" }} />
        <input placeholder="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} style={{ ...fieldStyle, flex: "1 1 110px" }} />
        <input placeholder="Longitude" value={lng} onChange={(e) => setLng(e.target.value)} style={{ ...fieldStyle, flex: "1 1 110px" }} />
        <input placeholder="Capacity" type="number" min={1} value={capacity} onChange={(e) => setCapacity(e.target.value)} style={{ ...fieldStyle, flex: "1 1 110px" }} />
      </div>

      <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 8 }}>
        Facilities
      </div>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 14 }}>
        {CANONICAL_FACILITIES.map((f) => (
          <FacilityCheckbox key={f} label={f} checked={canonical[f]} onChange={(v) => setCanonical((c) => ({ ...c, [f]: v }))} />
        ))}
        {EXTRA_FACILITIES.map((f) => (
          <FacilityCheckbox key={f} label={f} checked={extras[f]} onChange={(v) => setExtras((c) => ({ ...c, [f]: v }))} />
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
        <input placeholder="Contact person name" value={contactName} onChange={(e) => setContactName(e.target.value)} style={{ ...fieldStyle, flex: "1 1 200px" }} />
        <input placeholder="Contact phone" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} style={{ ...fieldStyle, flex: "1 1 160px" }} />
        <select value={status} onChange={(e) => setStatus(e.target.value as ShelterStatus)} style={{ ...fieldStyle, flex: "1 1 140px" }}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {STATUS_META[s].label}
            </option>
          ))}
        </select>
      </div>

      {formError && <div style={{ fontSize: 12, color: "var(--sev1)", marginBottom: 10 }}>{formError}</div>}

      <button onClick={submit} disabled={submitting} className="ps-btn-primary" style={registerButtonStyle}>
        {submitting ? "Registering…" : "Register shelter"}
      </button>

      {registeredCode && (
        <div
          style={{
            marginTop: 12,
            padding: "11px 13px",
            borderRadius: 5,
            background: "var(--ok-bg)",
            border: "1px solid var(--ok-border)",
            font: "400 12px/1.6 var(--font-interface)",
            color: "var(--sev5-ink)",
          }}
        >
          Registered as <strong style={{ font: "600 13px/1 var(--font-data)" }}>{registeredCode}</strong>. Give this
          code to the shelter's officer — they sign in with it from the landing page's "Shelter officer" card, no
          separate account needed.
        </div>
      )}
    </div>
  );
}

function FacilityCheckbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 6, font: "400 12px/1 var(--font-interface)", color: "var(--ink2)", cursor: "pointer", textTransform: "capitalize" }}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

function ShelterRow({ shelter }: { shelter: Shelter }) {
  const pct = occupancyPct(shelter);

  return (
    <div className="ps-row-hover" style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "12px 16px", borderBottom: "1px solid var(--border-soft)" }}>
      <span style={{ flex: 2, display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
        <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>{shelter.display_code}</span>
        <span style={{ font: "400 12px/1.3 var(--font-interface)", color: "var(--ink3)" }}>{shelter.name}</span>
        {(shelter.contact_name || shelter.contact_phone) && (
          <span style={{ font: "400 10.5px/1.4 var(--font-data)", color: "var(--ink4)" }}>
            {shelter.contact_name}
            {shelter.contact_name && shelter.contact_phone ? " · " : ""}
            {shelter.contact_phone}
          </span>
        )}
      </span>

      <span style={{ flex: 1, minWidth: 0, paddingRight: 8 }}>
        <span style={{ font: "500 12px/1 var(--font-data)", color: "var(--ink2)" }}>
          {shelter.current_occupancy}/{shelter.max_capacity} ({pct}%)
        </span>
        <div style={{ marginTop: 6, height: 4, borderRadius: 2, background: "var(--track)", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${pct}%`, background: occupancyColor(pct) }} />
        </div>
      </span>

      <span style={{ flex: 1.3, font: "400 12px/1.5 var(--font-interface)", color: "var(--ink3)" }}>
        {facilityTags(shelter.facilities).join(", ") || "—"}
      </span>

      <span style={{ flex: 1.3, display: "flex", flexWrap: "wrap", gap: 5 }}>
        {shelter.needs.length === 0 && <span style={{ font: "400 11px/1 var(--font-data)", color: "var(--ink4)" }}>none</span>}
        {shelter.needs.map((n) => (
          <span key={n} style={needChipStyle}>
            {n}
          </span>
        ))}
      </span>

      <span style={{ flex: 1 }}>
        <StatusPill status={shelter.status} />
      </span>
    </div>
  );
}

function StatusPill({ status }: { status: ShelterStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      style={{
        display: "inline-block",
        font: "500 10px/1 var(--font-data)",
        letterSpacing: "0.04em",
        padding: "4px 7px",
        borderRadius: 3,
        background: meta.bg,
        border: `1px solid ${meta.border}`,
        color: meta.ink,
      }}
    >
      {meta.label}
    </span>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
      <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>
        {title}
      </div>
      {children}
    </div>
  );
}

const fieldStyle: CSSProperties = {
  background: "var(--panel2)",
  border: "1px solid var(--border2)",
  borderRadius: 4,
  color: "var(--ink2)",
  padding: "7px 10px",
  fontSize: 12,
};

const registerButtonStyle: CSSProperties = {
  padding: "10px 18px",
  borderRadius: 5,
  border: "1px solid var(--accent)",
  background: "var(--accent)",
  color: "var(--on-accent)",
  font: "600 12px/1 var(--font-interface)",
  cursor: "pointer",
};

const needChipStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  font: "500 10px/1 var(--font-data)",
  padding: "3px 6px",
  borderRadius: 3,
  background: "var(--t1-bg)",
  border: "1px solid var(--t1-border)",
  color: "var(--alert-ink2)",
  textTransform: "capitalize",
};

