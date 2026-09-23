import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import CountUp from "../components/CountUp";
import FactorsPanel from "../components/FactorsPanel";
import { ConfidenceBadge, HandoffStatusBadge, TierBadge } from "../components/badges";
import { fetchDashboardSummary, fetchSurveys, fetchZoneHouseholds, type DashboardSummary, type HouseholdRanked } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const CRITICAL_THRESHOLD = 0.65;
const IMMEDIATE_THRESHOLD = 0.8;

/** "Situation summary" — PROTOTYPE/PS191 Platform.dc.html's sdma_official
 * home view: stat tiles, an alert banner, five KPI cards, then a 3-panel
 * row. Every number here is computed from real seeded data rather than
 * the prototype's fixed mock figures (rule 1/6) — "Live triggering
 * conditions" (rainfall mm, river gauge) is dropped since nothing in this
 * build exposes that as a standalone live reading outside a generated
 * forecast's factors[]; a real "Interagency handoffs" panel takes its
 * place instead. */
// Zone names are formatted "<name> (<block> block · ward N)" (app/seed.py) —
// pulled back out here so a field officer's header can say which block(s)
// their RLS-scoped zone list actually covers, instead of a hardcoded value
// that would drift the moment zone assignments change.
function assignedBlockLabel(zoneNames: string[]): string {
  const blocks = new Set(
    zoneNames.map((n) => n.match(/\(([^,)]+?)\s+block/i)?.[1]).filter((b): b is string => !!b),
  );
  if (blocks.size === 1) return `${[...blocks][0]} Block`;
  if (blocks.size > 1) return `${blocks.size} blocks`;
  return "Unassigned";
}

export default function Dashboard() {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [households, setHouseholds] = useState<HouseholdRanked[]>([]);
  const [unreviewedCount, setUnreviewedCount] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchDashboardSummary(token)
      .then(async (s) => {
        if (cancelled) return;
        setSummary(s);
        const perZone = await Promise.all(s.zones.items.map((z) => fetchZoneHouseholds(token, z.zone_id).catch(() => null)));
        if (cancelled) return;
        setHouseholds(perZone.flatMap((r) => r?.items ?? []));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    fetchSurveys(token)
      .then((r) => {
        if (!cancelled) setUnreviewedCount(r.items.filter((s) => s.review_status === "unreviewed").length);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [token]);

  const stats = useMemo(() => {
    if (!summary) return null;
    const zones = summary.zones.items;
    const criticalZones = zones.filter((z) => (z.risk_score_72h ?? 0) >= CRITICAL_THRESHOLD);
    const immediateHouseholds = households.filter((h) => h.priority_tier === "immediate");
    const immediateResidents = immediateHouseholds.reduce((sum, h) => sum + h.population_count, 0);
    const shelterCapacity = summary.shelters.items.reduce((sum, s) => sum + s.max_capacity, 0);
    const shelterOccupied = summary.shelters.items.reduce((sum, s) => sum + s.current_occupancy, 0);
    const moves = summary.relocations.items;
    const movesActive = moves.filter((m) => m.status === "assigned" || m.status === "in_transit").length;
    const movesArrived = moves.filter((m) => m.status === "arrived").length;
    const verified = households.filter((h) => h.data_confidence === "field_verified");
    const ages = households
      .map((h) => h.last_surveyed_at)
      .filter((d): d is string => !!d)
      .map((d) => (Date.now() - new Date(d).getTime()) / 86_400_000);
    const avgAge = ages.length ? Math.round(ages.reduce((a, b) => a + b, 0) / ages.length) : null;
    const topCritical = [...zones].sort((a, b) => (b.risk_score_72h ?? 0) - (a.risk_score_72h ?? 0)).slice(0, 3);

    return {
      criticalZones,
      totalZones: zones.length,
      immediateHouseholds: immediateHouseholds.length,
      immediateResidents,
      shelterCapacity,
      shelterOccupied,
      shelterHeadroom: shelterCapacity - shelterOccupied,
      movesActive,
      movesArrived,
      movesTotal: moves.length,
      dataCurrencyPct: households.length ? Math.round((verified.length / households.length) * 100) : 0,
      avgAge,
      topCritical,
    };
  }, [summary, households]);

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load dashboard: {error}</p>;
  if (!summary || !stats) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading dashboard…</p>;

  const isFieldOfficer = user?.role === "field_officer";
  const scopeNote = isFieldOfficer ? "in your zone only" : "all zones";

  return (
    <div data-reveal="" style={{ padding: 18 }}>
      <div style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 10 }}>
        {isFieldOfficer
          ? `My assigned zone: ${assignedBlockLabel(summary.zones.items.map((z) => z.name))}`
          : "District overview: Dima Hasao"}
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <StatTile label="Households tracked" value={households.length} note={scopeNote} />
        <StatTile
          label="Surveys unreviewed"
          value={unreviewedCount}
          color="var(--sev3-ink)"
          note={isFieldOfficer ? "your submissions" : "all submissions"}
        />
        <StatTile
          label="Handoffs pending"
          value={summary.handoffs.items.filter((h) => h.status !== "resolved").length}
          color="var(--sev3-ink)"
          note={isFieldOfficer ? "needs affecting your zone" : "all district needs"}
        />
      </div>

      {stats.immediateHouseholds > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 14,
            padding: "14px 16px",
            borderRadius: 6,
            background: "var(--alert-bg)",
            border: "1px solid var(--t1-border)",
            boxShadow: "0 0 24px -8px var(--sev2)",
            marginBottom: 16,
          }}
        >
          <div style={{ width: 3, alignSelf: "stretch", borderRadius: 2, background: "var(--sev2)", flex: "none" }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ font: "600 14px/1.3 var(--font-interface)", color: "var(--alert-ink)", marginBottom: 4 }}>
              {stats.criticalZones.length} zone{stats.criticalZones.length === 1 ? "" : "s"} at or above critical risk threshold
            </div>
            <div style={{ font: "400 12.5px/1.5 var(--font-interface)", color: "var(--alert-ink2)" }}>
              {stats.immediateResidents.toLocaleString("en-IN")} residents across {stats.immediateHouseholds} households in the
              immediate priority tier. Pre-staging recommended.
            </div>
          </div>
          <button onClick={() => navigate("/zones")} className="ps-btn-outline" style={alertButtonStyle}>
            Open priority queue
          </button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(216px, 1fr))", gap: 12, marginBottom: 16 }}>
        <KpiCard label="Critical zones" value={stats.criticalZones.length} valueColor="var(--sev2-ink)" suffix={`of ${stats.totalZones} mapped`} />
        <KpiCard label="Immediate tier" value={stats.immediateResidents} suffix="residents" note={`${stats.immediateHouseholds} households`} />
        <KpiCard
          label="Shelter headroom"
          value={stats.shelterHeadroom}
          valueColor="var(--sev5)"
          suffix={`of ${stats.shelterCapacity.toLocaleString("en-IN")}`}
          bar={stats.shelterCapacity > 0 ? stats.shelterOccupied / stats.shelterCapacity : 0}
        />
        <KpiCard
          label="Moves in progress"
          value={stats.movesActive}
          valueColor="var(--accent)"
          suffix={`of ${stats.movesTotal}`}
          note={`${stats.movesArrived} arrived`}
        />
        <KpiCard
          label="Data currency"
          value={stats.dataCurrencyPct}
          format={(n) => `${n}%`}
          valueColor="var(--sev3)"
          suffix="field-verified"
          note={stats.avgAge !== null ? `avg age ${stats.avgAge} days` : undefined}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(330px, 1fr))", gap: 12 }}>
        <Panel title="Critical zones" action={{ label: "Open map →", onClick: () => navigate("/zones") }}>
          {stats.topCritical.map((z) => (
            <button key={z.zone_id} onClick={() => navigate(`/zones/${z.zone_id}`)} className="ps-row-hover" style={panelRowButtonStyle}>
              <span
                style={{
                  width: 3,
                  height: 30,
                  borderRadius: 2,
                  flex: "none",
                  background: (z.risk_score_72h ?? 0) >= 0.8 ? "var(--sev1)" : (z.risk_score_72h ?? 0) >= 0.65 ? "var(--sev2)" : "var(--sev4)",
                }}
              />
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", font: "500 13px/1.3 var(--font-interface)", color: "var(--ink)" }}>{z.name}</span>
                <span style={{ display: "block", font: "400 10.5px/1.4 var(--font-data)", color: "var(--ink4)" }}>
                  {z.display_code} · {z.hazard_types.join(", ")}
                </span>
              </span>
              <span style={{ flex: "none", textAlign: "right" }}>
                <span style={{ display: "block", font: "600 15px/1.1 var(--font-data)", color: "var(--sev2-ink)" }}>
                  {z.risk_score_72h !== null ? Math.round(z.risk_score_72h * 100) : "—"}
                </span>
                <span style={{ display: "block", font: "400 9.5px/1.4 var(--font-data)", color: "var(--ink4)" }}>72H RISK</span>
              </span>
            </button>
          ))}
        </Panel>

        <Panel title="Priority queue">
          {summary.top_priority_households.slice(0, 5).map((h) => (
            <div key={h.household_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
              <button onClick={() => setExpanded(expanded === h.household_id ? null : h.household_id)} className="ps-row-hover" style={{ ...panelRowButtonStyle, flexDirection: "column", alignItems: "stretch", gap: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ font: "600 13px/1 var(--font-data)" }}>{h.display_code}</span>
                  <TierBadge tier={h.priority_tier} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <ConfidenceBadge confidence={h.data_confidence} />
                  <span style={{ font: "500 12px/1 var(--font-data)", color: "var(--ink3)" }}>priority {Math.round(h.priority_score * 100)}</span>
                </div>
              </button>
              {expanded === h.household_id && (
                <div style={{ padding: "0 16px 12px", display: "flex", flexDirection: "column", gap: 12 }}>
                  <FactorsPanel title="Priority factors" factors={h.priority_factors} />
                </div>
              )}
            </div>
          ))}
        </Panel>

        <Panel title="Interagency handoffs">
          {summary.handoffs.items.length === 0 && <p style={{ padding: "12px 16px", fontSize: 12, color: "var(--ink3)" }}>No open needs.</p>}
          {summary.handoffs.items.slice(0, 5).map((h) => (
            <div key={h.log_id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderBottom: "1px solid var(--border-soft)" }}>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", font: "500 13px/1.3 var(--font-interface)", color: "var(--ink)" }}>
                  {h.display_code} · {h.need_type}
                </span>
                <span style={{ display: "block", font: "400 10.5px/1.4 var(--font-data)", color: "var(--ink4)" }}>{h.agency}</span>
              </span>
              <HandoffStatusBadge status={h.status} />
            </div>
          ))}
        </Panel>
      </div>
    </div>
  );
}

function StatTile({ label, value, color, note }: { label: string; value: number; color?: string; note?: string }) {
  return (
    <div style={{ flex: 1, minWidth: 160, padding: "11px 15px", borderRadius: 6, background: "var(--panel)", border: "1px solid var(--border)" }}>
      <div style={{ font: "500 9.5px/1 var(--font-data)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 5 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span style={{ font: "600 21px/1 var(--font-data)", color: color ?? "var(--ink)" }}>
          <CountUp value={value} />
        </span>
        {note && <span style={{ font: "400 10.5px/1 var(--font-interface)", color: "var(--ink4)" }}>({note})</span>}
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  format,
  suffix,
  note,
  valueColor,
  bar,
}: {
  label: string;
  value: number;
  format?: (n: number) => string;
  suffix: string;
  note?: string;
  valueColor?: string;
  bar?: number;
}) {
  return (
    <div className="ps-card-hover" style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: "14px 16px" }}>
      <div style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 10 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ font: "600 32px/1 var(--font-data)", color: valueColor ?? "var(--ink)" }}>
          <CountUp value={value} format={format} />
        </span>
        <span style={{ font: "400 12px/1 var(--font-interface)", color: "var(--ink3)", whiteSpace: "nowrap" }}>{suffix}</span>
      </div>
      {bar !== undefined ? (
        <div style={{ marginTop: 10, height: 4, borderRadius: 2, background: "var(--track)", overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${Math.round(bar * 100)}%`, background: "var(--ocean)" }} />
        </div>
      ) : (
        note && <div style={{ marginTop: 10, font: "400 11px/1.4 var(--font-data)", color: "var(--ink3)" }}>{note}</div>
      )}
    </div>
  );
}

function Panel({ title, action, children }: { title: string; action?: { label: string; onClick: () => void }; children: ReactNode }) {
  return (
    <div style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
        <span style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)" }}>{title}</span>
        {action && (
          <button onClick={action.onClick} style={{ border: 0, background: "transparent", color: "var(--accent)", font: "500 11px/1 var(--font-interface)", cursor: "pointer" }}>
            {action.label}
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

const alertButtonStyle = {
  flex: "none",
  padding: "8px 13px",
  borderRadius: 4,
  border: "1px solid var(--sev2)",
  background: "var(--sev2)",
  color: "var(--on-sev)",
  font: "600 12px/1 var(--font-interface)",
  cursor: "pointer",
} as const;

const panelRowButtonStyle = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  width: "100%",
  padding: "11px 16px",
  border: 0,
  background: "transparent",
  cursor: "pointer",
  textAlign: "left",
} as const;
