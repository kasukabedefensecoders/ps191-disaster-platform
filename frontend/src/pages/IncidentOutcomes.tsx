import { useEffect, useState, type CSSProperties } from "react";
import { useSearchParams } from "react-router-dom";

import { OutcomeBadge, RiskChip, SampleDataBadge } from "../components/badges";
import { createIncidentOutcome, fetchIncidentOutcomes, fetchZones, type IncidentOutcome, type Zone } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

type TriState = "unknown" | "yes" | "no";

const TRI_TO_BOOL: Record<TriState, boolean | null> = { unknown: null, yes: true, no: false };

function nowForInput(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export default function IncidentOutcomes() {
  const { token, user } = useAuth();
  const [searchParams] = useSearchParams();
  const preselectedZoneId = searchParams.get("zone");
  const [zones, setZones] = useState<Zone[] | null>(null);
  const [zoneId, setZoneId] = useState<string | null>(preselectedZoneId);
  const [outcomes, setOutcomes] = useState<IncidentOutcome[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [occurredAt, setOccurredAt] = useState(nowForInput());
  const [shelterAdequate, setShelterAdequate] = useState<TriState>("unknown");
  const [routeHeldUp, setRouteHeldUp] = useState<TriState>("unknown");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!token) return;
    fetchZones(token)
      .then((r) => {
        setZones(r.items);
        if (r.items.length > 0) setZoneId((current) => current ?? r.items[0].zone_id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [token]);

  const loadOutcomes = () => {
    if (!token || !zoneId) return;
    fetchIncidentOutcomes(token, zoneId)
      .then((r) => setOutcomes(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(loadOutcomes, [token, zoneId]);

  const submit = async () => {
    if (!token || !zoneId) return;
    setSubmitting(true);
    setError(null);
    try {
      await createIncidentOutcome(token, zoneId, {
        occurred_at: new Date(occurredAt).toISOString(),
        shelter_adequate: TRI_TO_BOOL[shelterAdequate],
        route_held_up: TRI_TO_BOOL[routeHeldUp],
        notes: notes.trim() || null,
      });
      setNotes("");
      setShelterAdequate("unknown");
      setRouteHeldUp("unknown");
      loadOutcomes();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!zones) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading zones…</p>;

  const selectStyle: CSSProperties = {
    background: "var(--bg2)",
    border: "1px solid var(--border2)",
    color: "var(--ink2)",
    borderRadius: 4,
    padding: "6px 8px",
    fontSize: 12,
  };

  return (
    <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16, maxWidth: 720 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: 18 }}>Post-incident feedback</h2>
        <SampleDataBadge />
      </div>
      <p style={{ fontSize: 12, color: "var(--ink3)", margin: 0 }}>
        Ground-truth outcomes recorded here — shelter adequacy, whether the route held up, what actually happened — feed
        back into the risk-forecasting and allocation models (PRD §7.12). Each entry auto-links to the most recent 72h
        forecast generated for the zone before it occurred, so predicted risk can be checked against what really
        happened.
      </p>

      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <label style={{ fontSize: 12, color: "var(--ink3)" }}>Zone</label>
        <select value={zoneId ?? ""} onChange={(e) => setZoneId(e.target.value)} style={selectStyle}>
          {zones.map((z) => (
            <option key={z.zone_id} value={z.zone_id}>
              {z.display_code} · {z.name}
            </option>
          ))}
        </select>
      </div>

      {user?.role === "sdma_official" && (
        <div
          style={{
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: 12,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <div style={{ fontSize: 12, color: "var(--ink3)" }}>Record an outcome</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 11, color: "var(--ink3)" }}>
              Occurred at
              <input
                type="datetime-local"
                value={occurredAt}
                onChange={(e) => setOccurredAt(e.target.value)}
                style={selectStyle}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 11, color: "var(--ink3)" }}>
              Shelter adequate?
              <select value={shelterAdequate} onChange={(e) => setShelterAdequate(e.target.value as TriState)} style={selectStyle}>
                <option value="unknown">Unknown</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 11, color: "var(--ink3)" }}>
              Route held up?
              <select value={routeHeldUp} onChange={(e) => setRouteHeldUp(e.target.value as TriState)} style={selectStyle}>
                <option value="unknown">Unknown</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </label>
          </div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 11, color: "var(--ink3)" }}>
            Notes
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              style={{ ...selectStyle, resize: "vertical", fontFamily: "inherit" }}
              placeholder="What actually happened — road conditions, shelter capacity strain, anything the model should have weighted differently."
            />
          </label>
          <div>
            <button
              onClick={submit}
              disabled={submitting || !zoneId}
              className="ps-btn-confirm"
              style={{
                background: "var(--sev5)",
                border: "none",
                color: "var(--bg)",
                borderRadius: 4,
                padding: "6px 14px",
                fontSize: 12,
                fontWeight: 600,
                cursor: submitting ? "default" : "pointer",
              }}
            >
              {submitting ? "Recording…" : "Record outcome"}
            </button>
          </div>
        </div>
      )}

      <div>
        <div style={{ fontSize: 12, color: "var(--ink3)", marginBottom: 8 }}>History</div>
        {outcomes === null && <p style={{ fontSize: 12, color: "var(--ink3)" }}>Loading…</p>}
        {outcomes?.length === 0 && <p style={{ fontSize: 12, color: "var(--ink3)" }}>No outcomes recorded for this zone yet.</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {outcomes?.map((o) => (
            <div
              key={o.outcome_id}
              style={{
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: 10,
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "var(--font-data)", fontSize: 12, color: "var(--ink)" }}>
                  {new Date(o.occurred_at).toLocaleString()}
                </span>
                {o.predicted_score !== null && (
                  <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--ink3)" }}>
                    Predicted {o.predicted_horizon_hours}h risk
                    <RiskChip score={o.predicted_score} />
                  </span>
                )}
              </div>
              <div style={{ display: "flex", gap: 16 }}>
                <OutcomeBadge label="Shelter adequate" value={o.shelter_adequate} />
                <OutcomeBadge label="Route held up" value={o.route_held_up} />
              </div>
              {o.notes && <p style={{ fontSize: 12, color: "var(--ink2)", margin: 0 }}>{o.notes}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
