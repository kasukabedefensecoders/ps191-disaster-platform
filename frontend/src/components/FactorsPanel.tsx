import type { Factor } from "../lib/api";

/**
 * The one "explain this score" renderer (docs/DESIGN-SYSTEM.md §4) —
 * every score in this app (vulnerability, priority, shelter match) uses
 * this same component against the factors[] array the API already sent.
 * Per CLAUDE.md rule 1, this never recomputes or reverse-engineers a
 * score; it only formats what the backend returned.
 */
export default function FactorsPanel({ factors, title }: { factors: Factor[]; title?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {title && (
        <div style={{ fontFamily: "var(--font-data)", fontSize: 10, letterSpacing: "0.04em", color: "var(--ink4)", textTransform: "uppercase" }}>
          {title}
        </div>
      )}
      {factors.map((f) => (
        <div key={f.name} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--ink2)" }}>{f.name}</span>
            <span style={{ fontFamily: "var(--font-data)", color: "var(--ink3)" }}>
              {typeof f.input_value === "number" ? f.input_value.toLocaleString("en-IN") : String(f.input_value)}
            </span>
          </div>
          <div style={{ position: "relative", height: 5, background: "var(--track)", borderRadius: 3, overflow: "hidden" }}>
            <div
              style={{
                position: "absolute",
                inset: 0,
                width: `${Math.min(100, Math.round((f.contribution / f.weight) * 100))}%`,
                background: "var(--sev3)",
              }}
            />
          </div>
          <div style={{ fontFamily: "var(--font-data)", fontSize: 10, color: "var(--ink5)" }}>
            weight {f.weight.toFixed(2)} · contribution {f.contribution.toFixed(2)}
          </div>
        </div>
      ))}
    </div>
  );
}
