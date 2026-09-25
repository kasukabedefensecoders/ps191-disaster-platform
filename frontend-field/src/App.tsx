import { useLiveQuery } from "dexie-react-hooks";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";

import { db } from "./db";
import { ApiError, fetchZoneHouseholds, fetchZones, getMe, login, syncSurveys, type CurrentUser } from "./lib/api";

const TOKEN_KEY = "ps191_field_token";

export default function App() {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  });
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    if (!token) return;
    getMe(token)
      .then(setUser)
      .catch(() => {
        setToken(null);
        try {
          localStorage.removeItem(TOKEN_KEY);
        } catch {
          /* ignore */
        }
      });
  }, [token]);

  if (!token || !user) {
    return (
      <Login
        onLoggedIn={(t, u) => {
          setToken(t);
          setUser(u);
          try {
            localStorage.setItem(TOKEN_KEY, t);
          } catch {
            /* per-viewer convenience only */
          }
        }}
      />
    );
  }

  return <SurveyApp token={token} user={user} />;
}

function Login({ onLoggedIn }: { onLoggedIn: (token: string, user: CurrentUser) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { access_token } = await login(email, password);
      const user = await getMe(access_token);
      onLoggedIn(access_token, user);
    } catch {
      setError("Incorrect email or password, or the API is unreachable.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main style={page}>
      <form onSubmit={submit} style={card}>
        <h1 style={{ fontSize: 15, margin: 0 }}>RAKSHAK360 Field Survey</h1>
        <p style={{ fontSize: 12, color: "var(--ink3)", margin: 0 }}>Sign in once — the capture form works offline after that.</p>
        <input placeholder="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} style={input} />
        <input
          placeholder="Password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={input}
        />
        {error && <p style={{ color: "var(--sev1)", fontSize: 12, margin: 0 }}>{error}</p>}
        <button type="submit" disabled={submitting} style={button}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

const STRUCTURAL_OPTIONS = ["Kutcha", "Semi-pucca", "Pucca"];

function SurveyApp({ token, user }: { token: string; user: CurrentUser }) {
  const [zones, setZones] = useState<{ zone_id: string; display_code: string | null; name: string }[]>([]);
  const [households, setHouseholds] = useState<{ household_id: string; display_code: string | null }[]>([]);
  const [zoneId, setZoneId] = useState("");
  const [householdId, setHouseholdId] = useState<string>(""); // "" = new household
  const [form, setForm] = useState({
    population_count: "",
    children_count: "",
    elderly_count: "",
    assistance_needs_count: "",
    structural_condition: "Kutcha",
    notes: "",
  });
  const [geotag, setGeotag] = useState<{ lat: string; lon: string }>({ lat: "", lon: "" });
  const [saved, setSaved] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  // .orderBy() requires the field to be a declared Dexie index (db.ts only
  // indexes survey_id/synced); sorting the small in-memory array instead
  // avoids adding an index for a field this view is the only reader of.
  const queue = useLiveQuery(
    async () => (await db.surveys.toArray()).sort((a, b) => b.submitted_at.localeCompare(a.submitted_at)),
    [],
  );
  const pendingCount = queue?.filter((s) => !s.synced).length ?? 0;

  // Load zones — network-first, falling back to whatever was cached the
  // last time this device had connectivity (rule 5: this is a data-model
  // property, not just "the submit button still works").
  useEffect(() => {
    fetchZones(token)
      .then(async (res) => {
        setZones(res.items);
        await db.zonesCache.bulkPut(res.items.map((z) => ({ zone_id: z.zone_id, display_code: z.display_code, name: z.name })));
      })
      .catch(async () => {
        const cached = await db.zonesCache.toArray();
        setZones(cached);
      });
  }, [token]);

  useEffect(() => {
    if (!zoneId) {
      setHouseholds([]);
      return;
    }
    fetchZoneHouseholds(token, zoneId)
      .then(async (res) => {
        setHouseholds(res.items);
        await db.householdsCache.bulkPut(res.items.map((h) => ({ household_id: h.household_id, zone_id: zoneId, display_code: h.display_code })));
      })
      .catch(async () => {
        const cached = await db.householdsCache.where("zone_id").equals(zoneId).toArray();
        setHouseholds(cached);
      });
  }, [token, zoneId]);

  const useGpsLocation = () => {
    navigator.geolocation?.getCurrentPosition(
      (pos) => setGeotag({ lat: pos.coords.latitude.toFixed(6), lon: pos.coords.longitude.toFixed(6) }),
      () => setSyncMessage("Could not get GPS location — enter coordinates manually if this is a new household."),
    );
  };

  const saveOffline = async (e: FormEvent) => {
    e.preventDefault();
    const lat = parseFloat(geotag.lat);
    const lon = parseFloat(geotag.lon);
    const hasGeotag = !Number.isNaN(lat) && !Number.isNaN(lon);

    await db.surveys.add({
      survey_id: crypto.randomUUID(),
      zone_id: zoneId,
      household_id: householdId || null,
      submitted_at: new Date().toISOString(),
      payload: {
        population_count: Number(form.population_count) || 0,
        children_count: Number(form.children_count) || 0,
        elderly_count: Number(form.elderly_count) || 0,
        assistance_needs_count: Number(form.assistance_needs_count) || 0,
        structural_condition: form.structural_condition,
        notes: form.notes || null,
      },
      geotag: hasGeotag ? { type: "Point", coordinates: [lon, lat] } : null,
      synced: false,
      sync_error: null,
      synced_household_id: null,
    });

    setForm({ population_count: "", children_count: "", elderly_count: "", assistance_needs_count: "", structural_condition: "Kutcha", notes: "" });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const syncNow = async () => {
    const unsynced = (await db.surveys.toArray()).filter((s) => !s.synced);
    if (unsynced.length === 0) return;
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncSurveys(
        token,
        unsynced.map((s) => ({
          survey_id: s.survey_id,
          zone_id: s.zone_id,
          household_id: s.household_id,
          submitted_at: s.submitted_at,
          payload: s.payload,
          geotag: s.geotag,
        })),
      );
      for (const ok of result.synced) {
        await db.surveys.update(ok.survey_id, { synced: true, sync_error: null, synced_household_id: ok.household_id });
      }
      for (const err of result.errors) {
        await db.surveys.update(err.survey_id, { sync_error: err.error });
      }
      setSyncMessage(`Synced ${result.synced.length} of ${unsynced.length}${result.errors.length ? `, ${result.errors.length} failed` : ""}.`);
    } catch (err) {
      // A network failure here leaves every item exactly as queued — rule
      // 5's whole point: nothing is lost, the next sync attempt (possibly
      // a plain retry of the same request) picks up where this left off.
      setSyncMessage(err instanceof ApiError ? `Sync failed: ${err.message}` : "Sync failed — still offline?");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <main style={page}>
      <div style={{ ...card, width: 380 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h1 style={{ fontSize: 15, margin: 0 }}>RAKSHAK360 Field Survey</h1>
          <span style={{ fontSize: 11, color: "var(--ink3)" }}>{user.full_name}</span>
        </div>

        <form onSubmit={saveOffline} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label style={label}>
            Zone
            <select required value={zoneId} onChange={(e) => setZoneId(e.target.value)} style={input}>
              <option value="" disabled>
                Select a zone…
              </option>
              {zones.map((z) => (
                <option key={z.zone_id} value={z.zone_id}>
                  {z.display_code} — {z.name}
                </option>
              ))}
            </select>
          </label>

          <label style={label}>
            Household
            <select value={householdId} onChange={(e) => setHouseholdId(e.target.value)} style={input}>
              <option value="">New household (not surveyed before)</option>
              {households.map((h) => (
                <option key={h.household_id} value={h.household_id}>
                  {h.display_code}
                </option>
              ))}
            </select>
          </label>

          {!householdId && (
            <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
              <label style={{ ...label, flex: 1 }}>
                Lat
                <input value={geotag.lat} onChange={(e) => setGeotag({ ...geotag, lat: e.target.value })} style={input} />
              </label>
              <label style={{ ...label, flex: 1 }}>
                Lon
                <input value={geotag.lon} onChange={(e) => setGeotag({ ...geotag, lon: e.target.value })} style={input} />
              </label>
              <button type="button" onClick={useGpsLocation} style={{ ...button, background: "var(--track)", color: "var(--ink2)", flex: "none" }}>
                Use GPS
              </button>
            </div>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            <NumberField label="Population" value={form.population_count} onChange={(v) => setForm({ ...form, population_count: v })} />
            <NumberField label="Children <12" value={form.children_count} onChange={(v) => setForm({ ...form, children_count: v })} />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <NumberField label="Elderly 60+" value={form.elderly_count} onChange={(v) => setForm({ ...form, elderly_count: v })} />
            <NumberField
              label="Need assistance"
              value={form.assistance_needs_count}
              onChange={(v) => setForm({ ...form, assistance_needs_count: v })}
            />
          </div>

          <label style={label}>
            Structural condition
            <select value={form.structural_condition} onChange={(e) => setForm({ ...form, structural_condition: e.target.value })} style={input}>
              {STRUCTURAL_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>

          <label style={label}>
            Notes
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} style={{ ...input, height: 60 }} />
          </label>

          <button type="submit" style={button}>
            {saved ? "Saved ✓" : "Save (works offline)"}
          </button>
        </form>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--ink3)" }}>
              {pendingCount} queued · {(queue?.length ?? 0) - pendingCount} synced
            </span>
            <button onClick={syncNow} disabled={syncing || pendingCount === 0} style={{ ...button, width: "auto", padding: "6px 12px" }}>
              {syncing ? "Syncing…" : "Sync now"}
            </button>
          </div>
          {syncMessage && <p style={{ fontSize: 11, color: "var(--ink3)", margin: 0 }}>{syncMessage}</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 160, overflow: "auto" }}>
            {(queue ?? []).map((s) => (
              <div key={s.survey_id} style={{ fontSize: 11, display: "flex", justifyContent: "space-between", color: s.sync_error ? "var(--sev1)" : "var(--ink2)" }}>
                <span>{new Date(s.submitted_at).toLocaleTimeString()}</span>
                <span>{s.sync_error ? "error" : s.synced ? "synced" : "pending"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

function NumberField({ label: text, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label style={{ ...label, flex: 1 }}>
      {text}
      <input type="number" min={0} value={value} onChange={(e) => onChange(e.target.value)} style={input} />
    </label>
  );
}

const page: CSSProperties = {
  minHeight: "100vh",
  background: "var(--bg)",
  color: "var(--ink)",
  fontFamily: "var(--font-interface)",
  display: "flex",
  justifyContent: "center",
  padding: "24px 12px",
};
const card: CSSProperties = {
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 20,
  display: "flex",
  flexDirection: "column",
  gap: 14,
  width: 320,
  height: "fit-content",
};
const label: CSSProperties = { display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--ink3)" };
const input: CSSProperties = {
  background: "var(--panel2)",
  border: "1px solid var(--border)",
  borderRadius: 5,
  padding: "8px 10px",
  color: "var(--ink)",
  fontSize: 13,
  fontFamily: "var(--font-data)",
};
const button: CSSProperties = {
  background: "var(--sev3)",
  color: "var(--bg)",
  border: "none",
  borderRadius: 5,
  padding: "9px 0",
  fontWeight: 600,
  fontSize: 13,
  cursor: "pointer",
  fontFamily: "var(--font-interface)",
};
