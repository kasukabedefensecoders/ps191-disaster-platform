import { useEffect, useState } from "react";

import { HandoffStatusBadge, SampleDataBadge } from "../components/badges";
import { createHandoff, fetchHandoffs, fetchZones, updateHandoffStatus, type HandoffLog, type HandoffStatus, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const NEXT_STATUS: Record<HandoffStatus, HandoffStatus | null> = {
  open: "acknowledged",
  acknowledged: "in_progress",
  in_progress: "resolved",
  resolved: null,
};

/** PRD §7.13 — interagency handoff & coordination: flagged needs routed
 * to the responsible agency with acknowledgement status. Any role can
 * raise a need (a field officer spotting a medical/rescue need shouldn't
 * need an sdma_official to file it for them); status advances are
 * sdma_official-only, matching the backend's own gate. */
export default function Handoffs() {
  const { token, user } = useAuth();
  const [handoffs, setHandoffs] = useState<HandoffLog[] | null>(null);
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ need_type: "", agency: "", description: "", zone_id: "" });
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    if (!token) return;
    fetchHandoffs(token)
      .then((r) => setHandoffs(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);
  useEffect(() => {
    if (!token) return;
    fetchZones(token)
      .then((r) => {
        setZones(r.items);
        if (r.items.length > 0) setForm((f) => ({ ...f, zone_id: r.items[0].zone_id }));
      })
      .catch(() => {});
  }, [token]);

  const advance = async (h: HandoffLog) => {
    const next = NEXT_STATUS[h.status];
    if (!token || !next) return;
    setBusyId(h.log_id);
    try {
      await updateHandoffStatus(token, h.log_id, next);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const submit = async () => {
    if (!token || !form.need_type.trim() || !form.agency.trim() || !form.zone_id) return;
    setSubmitting(true);
    setError(null);
    try {
      await createHandoff(token, {
        need_type: form.need_type.trim(),
        agency: form.agency.trim(),
        description: form.description.trim() || null,
        zone_id: form.zone_id,
      });
      setForm((f) => ({ ...f, need_type: "", agency: "", description: "" }));
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!handoffs) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading handoffs…</p>;

  return (
    <div style={{ padding: 18, maxWidth: 760 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 18 }}>Interagency handoff</h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <SampleDataBadge />
          <button onClick={() => setShowForm((s) => !s)} className="ps-btn-outline" style={newButtonStyle}>
            {showForm ? "Cancel" : "New handoff"}
          </button>
        </div>
      </div>

      {showForm && (
        <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: 14, marginBottom: 16, display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              placeholder="Need type (e.g. Medical, Rescue, Transport)"
              value={form.need_type}
              onChange={(e) => setForm((f) => ({ ...f, need_type: e.target.value }))}
              style={{ ...fieldStyle, flex: 1, minWidth: 200 }}
            />
            <input
              placeholder="Agency"
              value={form.agency}
              onChange={(e) => setForm((f) => ({ ...f, agency: e.target.value }))}
              style={{ ...fieldStyle, flex: 1, minWidth: 200 }}
            />
            <select value={form.zone_id} onChange={(e) => setForm((f) => ({ ...f, zone_id: e.target.value }))} style={fieldStyle}>
              {zones?.map((z) => (
                <option key={z.zone_id} value={z.zone_id}>
                  {z.display_code}
                </option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            rows={2}
            style={{ ...fieldStyle, resize: "vertical" }}
          />
          <div>
            <button onClick={submit} disabled={submitting} className="ps-btn-confirm" style={submitButtonStyle}>
              {submitting ? "Routing…" : "Route to agency"}
            </button>
          </div>
        </div>
      )}

      {handoffs.length === 0 && <p style={{ fontSize: 12, color: "var(--ink3)" }}>No open needs.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {handoffs.map((h) => {
          const next = NEXT_STATUS[h.status];
          return (
            <div key={h.log_id} className="ps-card-hover" style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ font: "600 13px/1 var(--font-data)", color: "var(--ink)" }}>{h.display_code} · {h.need_type}</span>
                <HandoffStatusBadge status={h.status} />
              </div>
              <div style={{ font: "400 12px/1.4 var(--font-interface)", color: "var(--ink3)", marginTop: 6 }}>{h.agency}</div>
              {h.description && <div style={{ font: "400 12px/1.4 var(--font-interface)", color: "var(--ink2)", marginTop: 4 }}>{h.description}</div>}
              {next && user?.role === "sdma_official" && (
                <div style={{ marginTop: 8 }}>
                  <button onClick={() => advance(h)} disabled={busyId === h.log_id} className="ps-icon-btn" style={advanceButtonStyle}>
                    Mark {next.replace("_", " ")}
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

const fieldStyle = {
  background: "var(--panel2)",
  border: "1px solid var(--border2)",
  borderRadius: 4,
  color: "var(--ink2)",
  padding: "7px 10px",
  fontSize: 12,
} as const;

const newButtonStyle = {
  padding: "6px 12px",
  borderRadius: 4,
  border: "1px solid var(--accent)",
  background: "transparent",
  color: "var(--accent)",
  font: "600 11px/1 var(--font-interface)",
  cursor: "pointer",
} as const;

const submitButtonStyle = {
  background: "transparent",
  border: "1px solid var(--sev5)",
  color: "var(--sev5)",
  borderRadius: 4,
  padding: "6px 14px",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
} as const;

const advanceButtonStyle = {
  background: "transparent",
  border: "1px solid var(--border2)",
  color: "var(--ink2)",
  borderRadius: 4,
  padding: "5px 10px",
  fontSize: 12,
  cursor: "pointer",
} as const;
