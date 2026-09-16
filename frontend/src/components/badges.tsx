import { riskColor } from "../lib/riskColor";
import type { DataConfidence, HandoffStatus, PriorityTier } from "../lib/api";

const HANDOFF_COLOR: Record<HandoffStatus, string> = {
  open: "var(--sev1)",
  acknowledged: "var(--sev3)",
  in_progress: "var(--sev3)",
  resolved: "var(--sev5)",
};

// Phase 12: "status flag surfaced on the dashboard" — this is that flag.
export function HandoffStatusBadge({ status }: { status: HandoffStatus }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-data)",
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: "0.03em",
        padding: "2px 7px",
        borderRadius: 3,
        color: HANDOFF_COLOR[status],
        border: `1px solid ${HANDOFF_COLOR[status]}`,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {status.replace("_", " ")}
    </span>
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
const TIER_COLOR: Record<PriorityTier, string> = {
  immediate: "var(--sev1)",
  short_term: "var(--sev3)",
  medium_term: "var(--sev4)",
};

export function TierBadge({ tier }: { tier: PriorityTier }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-data)",
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: "0.04em",
        padding: "2px 7px",
        borderRadius: 3,
        color: TIER_COLOR[tier],
        border: `1px solid ${TIER_COLOR[tier]}`,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {TIER_LABEL[tier]}
    </span>
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
  const color = riskColor(score);
  return (
    <span style={{ fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 13, color }}>
      {score === null ? "—" : Math.round(score * 100)}
    </span>
  );
}

// rule 6: sample/seeded data is never presented without this marker.
export function SampleDataBadge() {
  return (
    <span
      style={{
        fontFamily: "var(--font-data)",
        fontSize: 9.5,
        letterSpacing: "0.05em",
        padding: "3px 7px",
        borderRadius: 3,
        background: "rgba(184,12,9,0.15)",
        color: "var(--sev1)",
        border: "1px solid rgba(184,12,9,0.4)",
        whiteSpace: "nowrap",
      }}
    >
      SAMPLE DATA
    </span>
  );
}
