import { useState, type CSSProperties } from "react";

import ThemeToggle from "../components/ThemeToggle";
import { SampleDataBadge } from "../components/badges";
import { updateMyShelter, type Shelter, type ShelterStatus } from "../lib/api";
import { useShelterAuth } from "../lib/ShelterAuthContext";
import { CANONICAL_FACILITIES, EXTRA_FACILITIES, STATUS_META, STATUS_OPTIONS, occupancyColor, occupancyPct } from "../lib/shelterDisplay";

/** The shelter officer's whole app: one shelter, one card. No nav rail, no
 * other shelters reachable — the code-based session (docs/TRD.md §10) only
 * ever unlocks GET/PATCH /shelters/me for this shelter, so there's nothing
 * else here to route to. */
export default function ShelterOfficerDashboard() {
  const { shelter, token, logout, refresh } = useShelterAuth();

  if (!shelter || !token) return null;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "12px 20px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg2)",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            width: 30,
            height: 30,
            flex: "none",
            borderRadius: 5,
            background: "var(--brand-deep)",
            border: "1px solid var(--blue)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            font: "600 12px/1 var(--font-data)",
            color: "var(--on-brand)",
          }}
        >
          RK
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ font: "600 13px/1.2 var(--font-interface)", color: "var(--ink)" }}>RAKSHAK360</div>
          <div style={{ font: "400 10px/1.3 var(--font-data)", color: "var(--ink4)" }}>SIH26191 · shelter officer</div>
        </div>
        <div style={{ flex: 1 }} />
        <SampleDataBadge />
        <ThemeToggle compact />
        <button onClick={logout} className="ps-row-hover" style={exitButtonStyle}>
          EXIT
        </button>
      </header>

      <main style={{ padding: 18, maxWidth: 640, margin: "0 auto" }}>
        <ShelterCard shelter={shelter} token={token} onSaved={refresh} />
      </main>
    </div>
  );
}

function ShelterCard({ shelter, token, onSaved }: { shelter: Shelter; token: string; onSaved: () => void }) {
  const [occupancy, setOccupancy] = useState(String(shelter.current_occupancy));
  const [newNeed, setNewNeed] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canonicalOn = new Set<string>(CANONICAL_FACILITIES.filter((f) => shelter.facilities[f] === true));
  const otherOn = new Set<string>(Array.isArray(shelter.facilities.other) ? (shelter.facilities.other as string[]) : []);
  const pct = occupancyPct(shelter);

  const patch = async (label: string, payload: Parameters<typeof updateMyShelter>[1]) => {
    setSaving(label);
    setError(null);
    try {
      await updateMyShelter(token, payload);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(null);
    }
  };

  const saveOccupancy = () => {
    const value = parseInt(occupancy, 10);
    if (!Number.isFinite(value) || value === shelter.current_occupancy) return;
    patch("occupancy", { current_occupancy: Math.max(0, Math.min(value, shelter.max_capacity)) });
  };

  const toggleFacility = (key: string, isExtra: boolean) => {
    if (isExtra) {
      const next = new Set(otherOn);
      next.has(key) ? next.delete(key) : next.add(key);
      patch(`facility:${key}`, { facilities: { ...shelter.facilities, other: [...next] } });
    } else {
      patch(`facility:${key}`, { facilities: { ...shelter.facilities, [key]: !canonicalOn.has(key) } });
    }
  };

  const setStatus = (status: ShelterStatus) => patch("status", { status });

  const addNeed = () => {
    const value = newNeed.trim().toLowerCase();
    if (!value || shelter.needs.includes(value)) return;
    setNewNeed("");
    patch("needs", { needs: [...shelter.needs, value] });
  };

  const removeNeed = (need: string) => patch("needs", { needs: shelter.needs.filter((n) => n !== need) });

  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
      <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 6 }}>
          {shelter.display_code}
        </div>
        <div style={{ font: "600 22px/1.3 var(--font-interface)", color: "var(--ink)", marginBottom: 8 }}>{shelter.name}</div>
        {(shelter.contact_name || shelter.contact_phone) && (
          <div style={{ font: "400 11.5px/1.5 var(--font-data)", color: "var(--ink3)" }}>
            Registered contact: {shelter.contact_name}
            {shelter.contact_name && shelter.contact_phone ? " · " : ""}
            {shelter.contact_phone}
          </div>
        )}
      </div>

      <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--border)" }}>
        <SectionLabel>Occupancy</SectionLabel>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
          <input
            type="number"
            min={0}
            max={shelter.max_capacity}
            value={occupancy}
            onChange={(e) => setOccupancy(e.target.value)}
            onBlur={saveOccupancy}
            style={{ ...fieldStyle, width: 90, fontSize: 20, fontWeight: 600, padding: "8px 10px" }}
          />
          <span style={{ font: "400 15px/1 var(--font-data)", color: "var(--ink3)" }}>/ {shelter.max_capacity} capacity</span>
          {saving === "occupancy" && <span style={{ font: "400 11px/1 var(--font-data)", color: "var(--ink4)" }}>saving…</span>}
        </div>
        <div style={{ height: 6, borderRadius: 3, background: "var(--track)", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${pct}%`, background: occupancyColor(pct), transition: "width 0.2s ease" }} />
        </div>
        <div style={{ marginTop: 6, font: "400 11px/1 var(--font-data)", color: occupancyColor(pct) }}>{pct}% occupied</div>
      </div>

      <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--border)" }}>
        <SectionLabel>Status</SectionLabel>
        <div style={{ display: "flex", gap: 7 }}>
          {STATUS_OPTIONS.map((s) => {
            const meta = STATUS_META[s];
            const isSelected = shelter.status === s;
            return (
              <button
                key={s}
                onClick={() => setStatus(s)}
                disabled={saving === "status"}
                style={{
                  flex: 1,
                  padding: "9px 6px",
                  borderRadius: 5,
                  border: `1px solid ${isSelected ? meta.border : "var(--border2)"}`,
                  background: isSelected ? meta.bg : "var(--panel2)",
                  color: isSelected ? meta.ink : "var(--ink3)",
                  font: "600 11px/1 var(--font-data)",
                  cursor: "pointer",
                }}
              >
                {meta.label}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--border)" }}>
        <SectionLabel>Facilities &amp; supplies</SectionLabel>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {CANONICAL_FACILITIES.map((f) => (
            <FacilityToggle key={f} label={f} checked={canonicalOn.has(f)} onChange={() => toggleFacility(f, false)} />
          ))}
          {EXTRA_FACILITIES.map((f) => (
            <FacilityToggle key={f} label={f} checked={otherOn.has(f)} onChange={() => toggleFacility(f, true)} />
          ))}
        </div>
      </div>

      <div style={{ padding: "18px 20px" }}>
        <SectionLabel>Urgent needs</SectionLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
          {shelter.needs.length === 0 && <span style={{ font: "400 12px/1 var(--font-data)", color: "var(--ink4)" }}>None flagged</span>}
          {shelter.needs.map((n) => (
            <span key={n} style={needChipStyle}>
              {n}
              <button onClick={() => removeNeed(n)} style={chipRemoveStyle} aria-label={`remove ${n}`}>
                ×
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            placeholder="e.g. medical, food, blankets…"
            value={newNeed}
            onChange={(e) => setNewNeed(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addNeed()}
            style={{ ...fieldStyle, flex: 1 }}
          />
          <button onClick={addNeed} className="ps-btn-outline" style={addNeedButtonStyle}>
            Add need
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px 20px", borderTop: "1px solid var(--border)", font: "400 12px/1.5 var(--font-interface)", color: "var(--sev1)" }}>
          {error}
        </div>
      )}
      <div style={{ padding: "10px 20px", borderTop: "1px solid var(--border)", font: "400 10.5px/1.5 var(--font-data)", color: "var(--ink4)" }}>
        Every change here saves immediately and appears on the SDMA dashboard's shelter view right away.
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 12 }}>
      {children}
    </div>
  );
}

function FacilityToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 7,
        padding: "8px 12px",
        borderRadius: 5,
        border: `1px solid ${checked ? "var(--accent)" : "var(--border2)"}`,
        background: checked ? "var(--blue-bg)" : "var(--panel2)",
        color: checked ? "var(--ink)" : "var(--ink3)",
        font: "500 12px/1 var(--font-interface)",
        textTransform: "capitalize",
        cursor: "pointer",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: checked ? "var(--accent)" : "var(--ink5)",
          flex: "none",
        }}
      />
      {label}
    </button>
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

const exitButtonStyle: CSSProperties = {
  padding: "6px 9px",
  borderRadius: 4,
  border: "1px solid var(--border2)",
  background: "transparent",
  color: "var(--ink3)",
  font: "500 10px/1 var(--font-data)",
  letterSpacing: "0.06em",
  cursor: "pointer",
};

const addNeedButtonStyle: CSSProperties = {
  padding: "7px 14px",
  borderRadius: 4,
  border: "1px solid var(--accent)",
  background: "transparent",
  color: "var(--accent)",
  font: "600 11px/1 var(--font-interface)",
  cursor: "pointer",
};

const needChipStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  font: "500 11px/1 var(--font-data)",
  padding: "5px 8px",
  borderRadius: 3,
  background: "var(--t1-bg)",
  border: "1px solid var(--t1-border)",
  color: "var(--alert-ink2)",
  textTransform: "capitalize",
};

const chipRemoveStyle: CSSProperties = {
  border: 0,
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  font: "600 12px/1 var(--font-data)",
  padding: 0,
  lineHeight: 1,
};
