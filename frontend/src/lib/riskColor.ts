/**
 * docs/DESIGN-SYSTEM.md §2.3's --sev1..--sev5 risk-severity bands. These are
 * for a zone's raw risk score, not a household's priority_tier (a different
 * measure with its own 3-band immediate/short_term/medium_term thresholds
 * from app/scoring/priority.py) — don't conflate the two.
 */
export type Theme = "dark" | "light";

const SEV_DARK = ["#B80C09", "#DB222A", "#FD9E02", "#8FC93A", "#32E875"] as const;
const SEV_LIGHT = ["#D32E22", "#D32E22", "#D98F1F", "#C9A93A", "#2E8A7D"] as const;

export function riskColor(score: number | null, theme: Theme = "dark"): string {
  const palette = theme === "dark" ? SEV_DARK : SEV_LIGHT;
  if (score === null) return palette[3];
  const risk = score * 100;
  if (risk >= 80) return palette[0];
  if (risk >= 65) return palette[1];
  if (risk >= 45) return palette[2];
  if (risk >= 28) return palette[3];
  return palette[4];
}
