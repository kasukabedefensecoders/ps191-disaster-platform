import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../lib/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/shelters", label: "Shelters" },
  { to: "/relocations", label: "Relocations" },
  { to: "/incident-outcomes", label: "Post-incident feedback" },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg)" }}>
      <nav
        style={{
          width: 200,
          flex: "none",
          background: "var(--bg2)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          padding: "16px 0",
        }}
      >
        <div style={{ padding: "0 16px 16px", fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 13, letterSpacing: "0.04em" }}>
          PS191
        </div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            style={({ isActive }) => ({
              padding: "10px 16px",
              fontSize: 13,
              color: isActive ? "var(--ink)" : "var(--ink3)",
              background: isActive ? "var(--row-sel)" : "transparent",
              borderLeft: isActive ? "2px solid var(--sev3)" : "2px solid transparent",
              textDecoration: "none",
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            height: 48,
            flex: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
            borderBottom: "1px solid var(--border)",
            background: "var(--bg2)",
          }}
        >
          <span style={{ fontSize: 13, color: "var(--ink3)" }}>Hazard Red-Zone &amp; Relocation Platform — Dima Hasao</span>
          {user && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12 }}>
              <span style={{ color: "var(--ink3)" }}>
                {user.full_name} · <span style={{ fontFamily: "var(--font-data)" }}>{user.role}</span>
              </span>
              <button
                onClick={logout}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border2)",
                  color: "var(--ink3)",
                  borderRadius: 4,
                  padding: "4px 10px",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Sign out
              </button>
            </div>
          )}
        </header>
        <main style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
