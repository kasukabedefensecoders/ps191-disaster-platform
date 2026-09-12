import { useState, type CSSProperties, type FormEvent } from "react";

import { useAuth } from "../lib/AuthContext";

export default function Login() {
  const { login, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password);
    } catch {
      // error is already surfaced via useAuth().error
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <form
        onSubmit={handleSubmit}
        style={{
          width: 320,
          padding: 28,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <div>
          <div style={{ fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 14, letterSpacing: "0.04em" }}>PS191</div>
          <div style={{ fontSize: 12, color: "var(--ink3)", marginTop: 4 }}>Hazard Red-Zone &amp; Relocation Platform</div>
        </div>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--ink3)" }}>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={inputStyle}
            autoComplete="username"
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--ink3)" }}>
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
            autoComplete="current-password"
          />
        </label>
        {error && <div style={{ fontSize: 12, color: "var(--sev1)" }}>{error}</div>}
        <button
          type="submit"
          disabled={submitting}
          style={{
            background: "var(--sev3)",
            color: "#070b16",
            border: "none",
            borderRadius: 4,
            padding: "9px 0",
            fontWeight: 600,
            fontSize: 13,
            cursor: submitting ? "default" : "pointer",
            opacity: submitting ? 0.7 : 1,
          }}
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

const inputStyle: CSSProperties = {
  background: "var(--panel2)",
  border: "1px solid var(--border)",
  borderRadius: 4,
  padding: "8px 10px",
  color: "var(--ink)",
  fontSize: 13,
};
