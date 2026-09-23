import type { Shelter, ShelterStatus } from "./api";

// Backend Schema §6.3: only power/water/medical/toilets are the canonical
// facility booleans matchFactors()'s "facility_count / 4" ratio counts —
// everything else (kitchen, blankets, food storage) lives in facilities.other,
// a plain string array, so it's tracked here but never divides into that ratio.
export const CANONICAL_FACILITIES = ["power", "water", "medical", "toilets"] as const;
export const EXTRA_FACILITIES = ["kitchen", "blankets", "food storage"] as const;

export const STATUS_META: Record<ShelterStatus, { label: string; bg: string; border: string; ink: string }> = {
  active: { label: "ACTIVE", bg: "var(--ok-bg)", border: "var(--ok-border)", ink: "var(--sev5-ink)" },
  standby: { label: "STANDBY", bg: "var(--t2-bg)", border: "var(--t2-border)", ink: "var(--sev3-ink)" },
  full: { label: "FULL", bg: "var(--t2-bg)", border: "var(--t2-border)", ink: "var(--sev3-ink)" },
  closed: { label: "CLOSED", bg: "var(--t1-bg)", border: "var(--t1-border)", ink: "var(--sev2-ink)" },
  damaged: { label: "DAMAGED", bg: "var(--t1-bg)", border: "var(--t1-border)", ink: "var(--sev2-ink)" },
};

// Only these 3 are offered on the registration form's dropdown and the
// inline/officer status edit — full/damaged stay possible states (e.g. a
// shelter a PATCH elsewhere marks "damaged") but aren't set by hand here.
export const STATUS_OPTIONS: ShelterStatus[] = ["active", "standby", "closed"];

export function occupancyPct(s: Pick<Shelter, "current_occupancy" | "max_capacity">): number {
  return s.max_capacity > 0 ? Math.min(100, Math.round((s.current_occupancy / s.max_capacity) * 100)) : 0;
}

export function occupancyColor(pct: number): string {
  if (pct > 95) return "var(--sev1)";
  if (pct >= 80) return "var(--sev3)";
  return "var(--sev5)";
}

export function facilityTags(facilities: Record<string, unknown>): string[] {
  const canonical = CANONICAL_FACILITIES.filter((k) => facilities[k] === true);
  const other = Array.isArray(facilities.other) ? (facilities.other as string[]) : [];
  return [...canonical, ...other];
}
