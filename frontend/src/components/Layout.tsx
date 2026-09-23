import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import ConfirmDialog from "./ConfirmDialog";
import ThemeToggle from "./ThemeToggle";
import { ReadOnlySessionBadge, SampleDataBadge } from "./badges";
import { useAuth } from "../lib/AuthContext";
import { resetDemoRelocations, type CurrentUser } from "../lib/api";

type NavItem = { to: string; label: string; end?: boolean; badge?: string };
type NavGroup = { label: string | null; items: NavItem[] };

const ROLE_BRAND: Record<CurrentUser["role"], { name: string; sub: string }> = {
  sdma_official: { name: "Red Zone & Relocation", sub: "SIH26191 · NDRF / MHA" },
  field_officer: { name: "Field Survey App", sub: "SIH26191 · field officer" },
  control_room: { name: "Monitoring Console", sub: "SIH26191 · control room" },
};

// Grouped exactly as PROTOTYPE/PS191 Platform.dc.html's nav rail (§5's
// screen inventory): section labels, item order, and which screens exist
// as their own nav destination vs. a panel reached by drilling in (72h
// forecast / SAR change detection / household assessment / priority
// ranking all live inside the zone detail screen here, not as separate
// routes — the prototype treats them as separate views because it has no
// real drill-down navigation to nest them under).
const NAV_BY_ROLE: Record<CurrentUser["role"], NavGroup[]> = {
  sdma_official: [
    { label: "Overview", items: [{ to: "/", label: "Situation summary", end: true }] },
    {
      label: "Risk",
      items: [
        { to: "/zones", label: "Red zone map" },
        { to: "/forecast", label: "72-hour forecast" },
        { to: "/change-detection", label: "SAR change detection" },
      ],
    },
    {
      label: "Population",
      items: [
        { to: "/households", label: "Household assessment" },
        { to: "/priority", label: "Priority ranking" },
      ],
    },
    {
      label: "Relocation",
      items: [
        { to: "/shelters", label: "Shelters & allocation" },
        { to: "/relocations", label: "Logistics tracker" },
        { to: "/routes", label: "Evacuation routes" },
      ],
    },
    {
      label: "Field & agencies",
      items: [
        { to: "/surveys", label: "Survey review" },
        { to: "/handoffs", label: "Interagency handoff" },
        { to: "/incident-outcomes", label: "Post-incident feedback" },
      ],
    },
  ],
  // No shelter management here — that's sdma_official (registration +
  // oversight) and each shelter's own officer (code-based sign-in via the
  // landing page's Shelter officer card) only.
  field_officer: [
    { label: null, items: [{ to: "/", label: "My Dashboard", end: true }] },
    {
      label: "Survey",
      items: [
        { to: "/zones", label: "Zone data" },
        { to: "/surveys", label: "My submissions" },
      ],
    },
    {
      label: "Relocation",
      items: [{ to: "/field-logistics", label: "Field officer logistics" }],
    },
  ],
  control_room: [{ label: null, items: [{ to: "/", label: "Situation dashboard", end: true }] }],
};

const ROLE_LABEL: Record<CurrentUser["role"], string> = {
  sdma_official: "SDMA official",
  field_officer: "Field officer",
  control_room: "Control room",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "U";
}

function useNowLabel(): string {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);
  return now.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function Layout() {
  const { token, user, logout } = useAuth();
  const groups = user ? NAV_BY_ROLE[user.role] : [];
  const nowLabel = useNowLabel();
  const [confirmingReset, setConfirmingReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  // Global — every screen reads relocation/survey data derived from
  // sample rows this can change, so the reset lives in the shared chrome
  // (not just the Logistics tracker page it started on) rather than
  // requiring a judge to navigate there first. A full reload (only on
  // success — a failed reset shows the error instead) is the simplest
  // correct way to get every currently-mounted page's own component state
  // (households, surveys, shelter occupancy counts, ...) back in sync with
  // the freshly reset rows, instead of wiring a global invalidation event
  // every page would need to subscribe to.
  const handleResetConfirm = async () => {
    if (!token) return;
    setConfirmingReset(false);
    setResetting(true);
    setResetError(null);
    try {
      await resetDemoRelocations(token);
      window.location.reload();
    } catch (err) {
      setResetError(err instanceof Error ? err.message : String(err));
      setResetting(false);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg)" }}>
      <nav
        style={{
          width: 236,
          flex: "none",
          background: "var(--bg2)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          overflowY: "auto",
        }}
      >
        <div style={{ padding: "16px 16px 14px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <div
              style={{
                width: 26,
                height: 26,
                flex: "none",
                borderRadius: 4,
                background: "var(--brand-deep)",
                border: "1px solid var(--blue)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                font: "600 11px/1 var(--font-data)",
                color: "var(--on-brand)",
              }}
            >
              RZ
            </div>
            <div>
              <div style={{ font: "600 13px/1.15 var(--font-interface)", color: "var(--ink)" }}>
                {user ? ROLE_BRAND[user.role].name : "PS191"}
              </div>
              <div style={{ font: "400 10px/1.4 var(--font-data)", color: "var(--ink4)", letterSpacing: "0.06em" }}>
                {user ? ROLE_BRAND[user.role].sub : ""}
              </div>
            </div>
          </div>
        </div>

        {groups.map((group, gi) => (
          <div key={gi}>
            {group.label && (
              <div
                style={{
                  padding: "14px 10px 6px",
                  font: "500 10px/1 var(--font-data)",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "var(--ink4)",
                }}
              >
                {group.label}
              </div>
            )}
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className="ps-nav-btn"
                style={({ isActive }) => ({
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  margin: gi === 0 && !group.label ? "10px 8px 4px" : "0 8px 2px",
                  padding: "8px 10px",
                  borderRadius: 5,
                  background: isActive ? "var(--blue-bg)" : "transparent",
                  boxShadow: isActive ? "inset 3px 0 0 var(--accent), 0 0 14px -6px var(--accent)" : "none",
                  textAlign: "left",
                  font: gi === 0 && !group.label ? "600 13px/1.2 var(--font-interface)" : "500 13px/1.2 var(--font-interface)",
                  color: isActive ? "var(--ink)" : "var(--ink2)",
                  textDecoration: "none",
                })}
              >
                <span style={{ flex: 1 }}>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}

        <div style={{ marginTop: "auto", padding: "14px 16px", borderTop: "1px solid var(--border)" }}>
          {user?.role === "sdma_official" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <FeedDot color="var(--sev5)" pulse label="IMD rainfall · live" />
              <FeedDot color="var(--sev3)" label="CWC gauge · historical" />
              <FeedDot color="var(--ink5)" label="GSI Bhusanket · dataset" ink="var(--ink4)" />
            </div>
          )}
          {user?.role === "field_officer" && (
            <div style={{ font: "400 10px/1.3 var(--font-data)", color: "var(--ink3)" }}>Assigned block: Haflong</div>
          )}
          {user?.role === "control_room" && (
            <div style={{ font: "400 10px/1.3 var(--font-data)", color: "var(--ink3)" }}>
              View-only session · no edit actions available
            </div>
          )}
        </div>
      </nav>

      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <header
          style={{
            flex: "none",
            minHeight: 54,
            borderBottom: "1px solid var(--border)",
            background: "var(--bg2)",
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px 16px",
            padding: "9px 18px",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div style={{ font: "600 13px/1.2 var(--font-interface)", color: "var(--ink)", whiteSpace: "nowrap" }}>
              Dima Hasao District, Assam
            </div>
            <div style={{ font: "400 10px/1.3 var(--font-data)", color: "var(--ink4)" }}>
              Pilot deployment · OpenStreetMap basemap
            </div>
          </div>
          <SampleDataBadge />
          {user?.role === "control_room" && <ReadOnlySessionBadge />}
          {user?.role === "sdma_official" && (
            <button onClick={() => setConfirmingReset(true)} disabled={resetting} className="ps-btn-outline" style={resetButtonStyle}>
              {resetting ? (
                <>
                  <span className="ps-spinner" /> Resetting…
                </>
              ) : (
                "Reset demo data"
              )}
            </button>
          )}
          {resetError && <span style={{ font: "400 11px/1.3 var(--font-data)", color: "var(--sev1)" }}>{resetError}</span>}
          <div style={{ flex: 1 }} />
          <div style={{ font: "400 11px/1.3 var(--font-data)", color: "var(--ink3)", textAlign: "right", whiteSpace: "nowrap" }}>
            <div>{nowLabel} IST</div>
            <div style={{ color: "var(--ink4)" }}>sync 40s ago · 18 kbps</div>
          </div>
          <ThemeToggle compact />
          {user && (
            <div style={{ display: "flex", alignItems: "center", gap: 9, paddingLeft: 14, borderLeft: "1px solid var(--border)" }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: "var(--brand-deep)",
                  border: "1px solid var(--blue)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  font: "600 11px/1 var(--font-data)",
                  color: "var(--on-brand)",
                  flex: "none",
                }}
              >
                {initials(user.full_name)}
              </div>
              <div>
                <div style={{ font: "500 12px/1.2 var(--font-interface)", color: "var(--ink)" }}>{user.full_name}</div>
                <div style={{ font: "400 10px/1.3 var(--font-data)", color: "var(--ink4)" }}>{ROLE_LABEL[user.role]}</div>
              </div>
              <button onClick={logout} className="ps-row-hover" style={exitButtonStyle}>
                EXIT
              </button>
            </div>
          )}
        </header>
        <main style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
          <Outlet />
        </main>
      </div>

      {confirmingReset && (
        <ConfirmDialog
          title="Reset demo data?"
          body="This replaces every current relocation, survey and generated 72-hour forecast with a fresh copy of the demo scenario — any manual status changes since the last reset will be lost."
          confirmLabel="Reset"
          onCancel={() => setConfirmingReset(false)}
          onConfirm={handleResetConfirm}
        />
      )}
    </div>
  );
}

function FeedDot({ color, label, pulse, ink }: { color: string; label: string; pulse?: boolean; ink?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span
        style={{ width: 6, height: 6, borderRadius: "50%", background: color, animation: pulse ? "pulseDot 2s ease-in-out infinite" : undefined }}
      />
      <span style={{ font: "400 10px/1.3 var(--font-data)", color: ink ?? "var(--ink3)" }}>{label}</span>
    </div>
  );
}

const exitButtonStyle = {
  padding: "6px 9px",
  borderRadius: 4,
  border: "1px solid var(--border2)",
  background: "transparent",
  color: "var(--ink3)",
  font: "500 10px/1 var(--font-data)",
  letterSpacing: "0.06em",
  cursor: "pointer",
} as const;

const resetButtonStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "6px 10px",
  borderRadius: 4,
  border: "1px solid var(--accent)",
  background: "transparent",
  color: "var(--accent)",
  font: "600 10.5px/1 var(--font-interface)",
  cursor: "pointer",
} as const;
