import type { ReactNode } from "react";

import { riskColor } from "../lib/riskColor";
import { useTheme } from "../lib/ThemeContext";
import type { DataConfidence, HandoffStatus, PriorityTier } from "../lib/api";

/** Filled tier/status pill — ported from the prototype's "IMMEDIATE"/
 * "REVIEW"/"HANDOFF" chips (PS191 Platform.dc.html: padding 4px 6px,
 * radius 3, a tinted surface + border + matched ink per severity step,
 * docs/DESIGN-SYSTEM.md §2.3's "matched ink and surface pair"). */
function Pill({ bg, border, ink, children }: { bg: string; border: string; ink: string; children: ReactNode }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-data)",
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: "0.03em",
        padding: "4px 6px",
        borderRadius: 3,
        background: bg,
        color: ink,
        border: `1px solid ${border}`,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

const HANDOFF_PILL: Record<HandoffStatus, { bg: string; border: string; ink: string }> = {
  open: { bg: "var(--t1-bg)", border: "var(--t1-border)", ink: "var(--sev2-ink)" },
  acknowledged: { bg: "var(--t2-bg)", border: "var(--t2-border)", ink: "var(--sev3-ink)" },
  in_progress: { bg: "var(--t2-bg)", border: "var(--t2-border)", ink: "var(--sev3-ink)" },
  resolved: { bg: "var(--ok-bg)", border: "var(--ok-border)", ink: "var(--sev5-ink)" },
};

// Phase 12: "status flag surfaced on the dashboard" — this is that flag.
export function HandoffStatusBadge({ status }: { status: HandoffStatus }) {
  const p = HANDOFF_PILL[status];
  return (
    <Pill bg={p.bg} border={p.border} ink={p.ink}>
      {status.replace("_", " ")}
    </Pill>
  );
}

const TIER_LABEL: Record<PriorityTier, string> = {
  immediate: "Immediate",
  short_term: "Short-term",
  medium_term: "Medium-term",
};
// app/scoring/priority.py's prio_tier thresholds (0.68 / 0.48), not the
// design system's separate 5-band raw-risk scale — same colour tokens,
// different axis (see riskColor.ts's own note on this distinction).
const TIER_PILL: Record<PriorityTier, { bg: string; border: string; ink: string }> = {
  immediate: { bg: "var(--t1-bg)", border: "var(--t1-border)", ink: "var(--sev2-ink)" },
  short_term: { bg: "var(--t2-bg)", border: "var(--t2-border)", ink: "var(--sev3-ink)" },
  medium_term: { bg: "var(--t3-bg)", border: "var(--t3-border)", ink: "var(--sev4-ink)" },
};

export function TierBadge({ tier }: { tier: PriorityTier }) {
  const p = TIER_PILL[tier];
  return (
    <Pill bg={p.bg} border={p.border} ink={p.ink}>
      {TIER_LABEL[tier]}
    </Pill>
  );
}

const CONFIDENCE_LABEL: Record<DataConfidence, string> = {
  field_verified: "Field-verified",
  baseline: "Govt baseline only",
  due_for_reverification: "Re-verification due",
};
const CONFIDENCE_COLOR: Record<DataConfidence, string> = {
  field_verified: "var(--sev5)",
  baseline: "var(--sev3)",
  due_for_reverification: "var(--sev1)",
};

// rule 3: confidence state travels with every response that returns a zone
// or household — this is the one place it's rendered.
export function ConfidenceBadge({ confidence }: { confidence: DataConfidence }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--ink3)" }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: CONFIDENCE_COLOR[confidence], flex: "none" }} />
      {CONFIDENCE_LABEL[confidence]}
    </span>
  );
}

// PRD §7.12's two ground-truth questions ("was the shelter adequate",
// "did the route hold up") are tri-state — an authority may not yet know
// (null) — so this renders three states, not a boolean toggle.
export function OutcomeBadge({ label, value }: { label: string; value: boolean | null }) {
  const color = value === null ? "var(--ink3)" : value ? "var(--sev5)" : "var(--sev1)";
  const text = value === null ? "Unknown" : value ? "Yes" : "No";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11 }}>
      <span style={{ color: "var(--ink3)" }}>{label}</span>
      <span style={{ fontFamily: "var(--font-data)", fontWeight: 600, color }}>{text}</span>
    </span>
  );
}

export function RiskChip({ score }: { score: number | null }) {
  const { theme } = useTheme();
  const color = riskColor(score, theme);
  return (
    <span style={{ fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 13, color }}>
      {score === null ? "—" : Math.round(score * 100)}
    </span>
  );
}

// rule 6: sample/seeded data is never presented without this marker —
// ported verbatim from the prototype's header chip (line 348: an outlined
// mono pill, not a filled red one).
export function SampleDataBadge() {
  return (
    <span
      style={{
        fontFamily: "var(--font-data)",
        fontWeight: 500,
        fontSize: 9,
        letterSpacing: "0.1em",
        padding: "5px 7px",
        borderRadius: 3,
        border: "1px solid var(--border2)",
        color: "var(--ink3)",
        whiteSpace: "nowrap",
      }}
    >
      SAMPLE DATA
    </span>
  );
}

// Prototype header chip (line 350): shown only for a read-only role.
export function ReadOnlySessionBadge() {
  return (
    <span
      style={{
        fontFamily: "var(--font-data)",
        fontWeight: 500,
        fontSize: 9,
        letterSpacing: "0.1em",
        padding: "5px 7px",
        borderRadius: 3,
        border: "1px solid var(--sev3)",
        background: "var(--t2-bg)",
        color: "var(--warn-ink)",
        whiteSpace: "nowrap",
      }}
    >
      READ-ONLY SESSION
    </span>
  );
}
