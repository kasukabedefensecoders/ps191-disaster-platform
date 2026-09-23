import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../lib/AuthContext";
import { useShelterAuth } from "../lib/ShelterAuthContext";

export type RoleKey = "sdma_official" | "field_officer" | "control_room" | "shelter_officer";

// Seeded demo accounts (backend/app/seed.py's SEED_USERS/SEED_PASSWORD) —
// real auth is still the account behind the credentials (role comes back
// from /auth/me, not from anything picked here), so these buttons only
// prefill the form as a demo convenience and to show what each role can do,
// mirroring PROTOTYPE/PS191 Platform.dc.html's SDMA/FIELD/CONTROL picker.
// shelter_officer has no `email` — it's a wholly different credential (a
// bare shelter code, no account behind it, see docs/TRD.md §10), which is
// exactly why selecting it swaps the form fields below instead of just
// prefilling them.
const ROLE_INFO: Record<RoleKey, { code: string; sub: string; email?: string }> = {
  sdma_official: { code: "SDMA", sub: "full access", email: "sdma.official@ps191.dev" },
  field_officer: { code: "FIELD", sub: "survey only", email: "field.officer@ps191.dev" },
  control_room: { code: "CONTROL", sub: "read-only", email: "control.room@ps191.dev" },
  shelter_officer: { code: "SHELTER", sub: "shelter management" },
};
const DEMO_PASSWORD = "ps191-demo-pass";

/** Sign-in as a modal over the landing page, not a separate /login route —
 * the landing page (hero, map, role cards) stays visible and mounted
 * underneath, and the URL never changes to something a stale bookmark or a
 * previous session could leave in a nested-route state. That last part
 * matters here specifically: RootGate (App.tsx) swaps Landing in for
 * *any* path under "/" while unauthenticated without touching the URL bar,
 * so a visitor who arrived at, say, "#/relocations" while logged out would
 * — once authenticated, without the explicit navigate() below — land on
 * that nested route instead of the dashboard home.
 *
 * One modal, four roles: selecting "Shelter officer" swaps the email/
 * password fields for a single shelter-code field and routes through
 * ShelterAuthContext instead of AuthContext on submit — a genuinely
 * different credential (docs/TRD.md §10), not just a different account, so
 * it gets its own branch here rather than pretending it's a fourth account
 * with a blank password. */
export default function SignInModal({ onClose, initialRole = null }: { onClose: () => void; initialRole?: RoleKey | null }) {
  const { login, error: accountError } = useAuth();
  const { login: shelterLogin, error: shelterError } = useShelterAuth();
  const navigate = useNavigate();
  // Lazy initializers so opening the modal pre-selected to a role (a landing
  // page role-card click) prefills exactly like clicking that role's button
  // inside the modal would — no separate effect needed to keep them in sync.
  const [email, setEmail] = useState(() => (initialRole ? ROLE_INFO[initialRole].email ?? "" : ""));
  const [password, setPassword] = useState(() => (initialRole && ROLE_INFO[initialRole].email ? DEMO_PASSWORD : ""));
  const [shelterCode, setShelterCode] = useState("");
  const [selectedRole, setSelectedRole] = useState<RoleKey | null>(initialRole);
  const [submitting, setSubmitting] = useState(false);

  const [closing, setClosing] = useState(false);
  const isShelter = selectedRole === "shelter_officer";
  const error = isShelter ? shelterError : accountError;

  // A cancelled sign-in (Escape, backdrop, ✕) gets the fade-and-settle exit
  // (modalCardOut/modalOverlayOut in tokens.css) before actually unmounting.
  // A *successful* one skips this — the moment login() resolves, RootGate
  // swaps Landing (and everything under it, this modal included) for the
  // authenticated app in the same render, so there's no frame left to
  // animate into; requestClose here would just be dead code on that path.
  const requestClose = () => {
    setClosing(true);
    setTimeout(onClose, 150);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") requestClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pickRole = (role: RoleKey) => {
    setSelectedRole(role);
    const info = ROLE_INFO[role];
    if (info.email) {
      setEmail(info.email);
      setPassword(DEMO_PASSWORD);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (isShelter) {
        const displayCode = await shelterLogin(shelterCode);
        navigate(`/shelter-dashboard/${displayCode}`, { replace: true });
      } else {
        await login(email, password);
        navigate("/", { replace: true });
      }
      onClose();
    } catch {
      // error is already surfaced via accountError/shelterError above
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Sign in"
      onClick={requestClose}
      data-modal-overlay=""
      data-closing={closing}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(4, 8, 18, 0.6)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        data-modal-card=""
        data-closing={closing}
        style={{
          width: "100%",
          maxWidth: 400,
          maxHeight: "calc(100vh - 40px)",
          overflowY: "auto",
          background: "var(--bg2)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          boxShadow: "var(--shadow)",
          padding: 30,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
          <div>
            <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 8 }}>
              {isShelter ? "Shelter code sign-in" : "Authorised access only"}
            </div>
            <div style={{ font: "600 20px/1.25 var(--font-interface)", color: "var(--ink)" }}>Sign in</div>
          </div>
          <button type="button" onClick={requestClose} aria-label="Close" style={closeButtonStyle}>
            ✕
          </button>
        </div>
        <div style={{ font: "400 12px/1.6 var(--font-data)", color: "var(--ink3)", marginBottom: 20 }}>Dima Hasao district · Assam SDMA</div>

        {isShelter ? (
          <>
            <label style={fieldLabel}>Shelter code</label>
            <input
              required
              autoFocus
              value={shelterCode}
              onChange={(e) => setShelterCode(e.target.value)}
              placeholder="e.g. SH-01"
              style={{ ...inputStyle, textTransform: "uppercase" }}
              autoComplete="off"
            />
          </>
        ) : (
          <>
            <label style={fieldLabel}>Officer email</label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              autoComplete="username"
            />
            <label style={fieldLabel}>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              autoComplete="current-password"
            />
          </>
        )}

        <label style={fieldLabel}>Role</label>
        <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
          {(Object.keys(ROLE_INFO) as RoleKey[]).map((role) => {
            const info = ROLE_INFO[role];
            const isSelected = selectedRole === role;
            return (
              <button
                key={role}
                type="button"
                onClick={() => pickRole(role)}
                className={isSelected ? "ps-glow-accent" : undefined}
                style={{
                  flex: 1,
                  padding: "10px 5px",
                  borderRadius: 5,
                  border: `1px solid ${isSelected ? "var(--accent)" : "var(--border2)"}`,
                  background: isSelected ? "var(--blue-bg)" : "var(--panel)",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <span style={{ display: "block", font: "600 10px/1.3 var(--font-data)", color: "var(--ink)" }}>{info.code}</span>
                <span style={{ display: "block", font: "400 8.5px/1.3 var(--font-data)", color: "var(--ink4)", marginTop: 2 }}>{info.sub}</span>
              </button>
            );
          })}
        </div>

        {error && <div style={{ fontSize: 12, color: "var(--sev1)", marginBottom: 12 }}>{error}</div>}

        <button
          type="submit"
          disabled={submitting || (isShelter && !shelterCode.trim())}
          className="ps-btn-primary"
          style={signInButtonStyle}
        >
          {submitting ? "Signing in…" : isShelter ? "Open shelter dashboard" : "Sign in to district dashboard"}
        </button>

        {isShelter && (
          <div
            style={{
              marginTop: 16,
              padding: "11px 13px",
              borderRadius: 5,
              background: "var(--panel)",
              border: "1px solid var(--border)",
              font: "400 10.5px/1.6 var(--font-data)",
              color: "var(--ink3)",
            }}
          >
            This code is issued when an SDMA official registers your shelter. It opens only this one shelter's
            dashboard — nothing else on the platform.
          </div>
        )}
      </form>
    </div>
  );
}

const fieldLabel: CSSProperties = {
  display: "block",
  font: "500 11px/1 var(--font-data)",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "var(--ink4)",
  marginBottom: 7,
};

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "12px 13px",
  borderRadius: 5,
  border: "1px solid var(--border2)",
  background: "var(--panel)",
  color: "var(--ink)",
  font: "400 14px/1 var(--font-data)",
  marginBottom: 16,
};

const signInButtonStyle: CSSProperties = {
  width: "100%",
  padding: 14,
  borderRadius: 5,
  border: "1px solid var(--accent)",
  background: "var(--accent)",
  color: "var(--on-accent)",
  font: "600 14px/1 var(--font-interface)",
  cursor: "pointer",
  minHeight: 48,
};

const closeButtonStyle: CSSProperties = {
  flex: "none",
  width: 28,
  height: 28,
  borderRadius: 5,
  border: "1px solid var(--border2)",
  background: "transparent",
  color: "var(--ink3)",
  cursor: "pointer",
  font: "400 13px/1 var(--font-data)",
};
