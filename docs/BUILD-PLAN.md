# Build Plan

## Intelligent Hazard Red-Zone & Relocation Platform — SIH26191

| | |
|---|---|
| **Purpose** | Resolve the four known schema/prototype conflicts, flag two more the team missed, and set a build order for the hackathon MVP. |
| **Status** | Recommendation — needs team sign-off before Phase 0 starts, since every downstream phase reads the resolved enums. |
| **Relates to** | CLAUDE.md "Known conflicts"; `docs/BACKEND-SCHEMA.md` §3, §5.3–5.6; `docs/PRD.md` §7.1–7.3, §7.10; `docs/TRD.md` §5, §8.1 |

---

## Part 1 — Conflict resolution

Both documents were written independently; neither is automatically right. Below, each conflict is decided by asking which side the *rest of the system* already depends on, not which document is newer.

### 1.1 Priority tier values — schema wins

| | Value |
|---|---|
| **Schema** | `immediate` / `short_term` / `medium_term` |
| **Prototype** | `immediate` / `short` / `medium` |
| **Decision** | **Schema.** Use `immediate` / `short_term` / `medium_term` as the persisted enum and API value. |

**Why:** the prototype's `short`/`medium` are internal JS variable shorthand (`prioTier(s) { return s >= 68 ? 'immediate' : s >= 48 ? 'short' : 'medium'; }`), not a deliberate naming decision — nothing in the design system or PRD treats the short form as meaningful. The PRD itself (§1, §5, §7.3) always writes "short-term" / "medium-term" in prose, and the schema's longer form matches that wording directly rather than abbreviating it. Porting `prioTier()` to Python should return the schema's values directly; the frontend can still *display* "Short-term" as a label without the persisted value being the ambiguous short form.

**Action:** no schema change needed. Note for the port: `prioTier()` return values change from `'short'`/`'medium'` to `'short_term'`/`'medium_term'`.

### 1.2 Score range — schema wins, with a rescale note

| | Value |
|---|---|
| **Schema** | `numeric(5,4)`, checked `between 0 and 1` |
| **Prototype** | integers, 0–100 |
| **Decision** | **Schema.** Every score column stores 0–1. |

**Why, with a detail the conflict table doesn't show:** the prototype is not uniformly 0–100. Checking the actual seed data (`ZONES` array, line ~1627), `susp` (susceptibility) is already stored 0–1 (`susp:0.91`, `susp:0.84`, …) and is read directly into the priority factor row with no `/100`. Only `vulnScore`, `prioScore`, `matchScore`, and the zone's `risk`/forecast values are 0–100. So the prototype itself is already inconsistent about scale — the schema's uniform 0–1 is the fix, not a foreign convention being imposed.

**Porting rule:** don't divide the *computed score* by 100 — rescale the *weights* so they sum to 1.0 instead of 100 (`28 → 0.28`, `24 → 0.24`, …), and rescale the two `prioTier` thresholds the same way (`68 → 0.68`, `48 → 0.48`). This keeps every intermediate `contribution` value correctly proportioned. Verify the Python port against the prototype's own worked examples — e.g. hand-check `HH-112`'s vulnerability score and factor contributions match after rescaling, not just the final tier.

The dashboard is free to *display* `round(score * 100)` for a 0–100-looking number; the API and database stay 0–1 per schema. This is consistent with rule 1 (every score returns its factors) — the factors travel in whatever unit the score is in.

### 1.3 Structural condition — prototype wins

| | Value |
|---|---|
| **Schema** | `sound` / `at_risk` / `unsafe` / `unknown` |
| **Prototype** | `Kutcha` / `Semi-pucca` / `Pucca` |
| **Decision** | **Prototype.** Replace the schema enum with `Kutcha` / `Semi-pucca` / `Pucca` / `unknown`. |

**Why:** this is the one CLAUDE.md already flags as mattering most, and the prototype code confirms it concretely — `STRUCT = { 'Kutcha':1, 'Semi-pucca':0.55, 'Pucca':0.2 }` is a real, already-agreed vulnerability-weight mapping feeding the highest-weighted factor (28 of 100) in `vulnFactors()`. `sound`/`at_risk`/`unsafe` has no defined mapping to that weight — adopting it would mean inventing a new mapping from scratch for no benefit, and losing the field-officer-recognizable category a survey form actually needs (PRD §7.10: "a structured checklist matching the vulnerability-assessment fields"). `unknown` is kept as the schema's pre-survey default (`structural_condition ... default 'unknown'` already exists and should stay).

**Action:** this is a real schema change. Update `docs/BACKEND-SCHEMA.md` §3 (`structural_condition` enum) and §5.4/§5.6 (default value, JSONB example in §6.5) in the same commit that changes the model, per CLAUDE.md's working-style rule.

### 1.4 Survey review status — prototype wins

| | Value |
|---|---|
| **Schema** | `unreviewed` / `confirmed` / `corrected` |
| **Prototype** | `unreviewed` / `approved` / `flagged` |
| **Decision** | **Prototype.** Replace the schema enum with `unreviewed` / `approved` / `flagged`. |

**Why:** the prototype isn't just naming things differently — it has two concrete, built supervisor actions (Survey Review screen: "approve and flag actions", per `docs/DESIGN-SYSTEM.md` §5) with real UI chips (`RV = { unreviewed:..., approved:..., flagged:... }`) and a real seeded example of each state, including *why* something gets flagged (`SV-4455`: "GPS geotag 940 m outside zone boundary"). `confirmed`/`corrected` reads reasonably on paper but corresponds to no built interaction — "corrected" in particular is ambiguous about whether it means the payload was edited or just re-labeled. PRD §7.10's own open decision talks about "supervisor downgrade/correction," which is close to but not identical to either enum; the team should treat the PRD's wording as intent, not a literal enum name, and the prototype's `approved`/`flagged` as the concrete implementation of that intent.

**Action:** schema change. Update `docs/BACKEND-SCHEMA.md` §3 (`review_status` enum) in the same commit.

---

## Part 2 — Two more disagreements the four-item list missed

Both surfaced by checking the schema's actual columns against what the prototype's scoring code and screen inventory require it to have — not a difference in *values*, but a **missing column**.

### 2.1 Households have no `data_confidence` — but the schema's own rules require one

CLAUDE.md rule 3 states plainly: *"Zones and households carry their verification state — baseline, field_verified, due_for_reverification — and the last-verified timestamp, in every response that returns them."* But `docs/BACKEND-SCHEMA.md` §5.4 (`households`) has no `data_confidence` column — only `last_surveyed_at`. The enum and the confidence column exist solely on `zones` (§5.3).

The prototype confirms households need their own, separate confidence state: every household row carries `source: 'field'` or `source: 'census'`, and `prioFactors()` reads it directly — `const conf = h.source === 'field' ? 0.35 : 1;` — as the "Data uncertainty margin" factor (weight 8), which is the concrete mechanism behind rule 4 (baseline-only households score higher). A zone can be `field_verified` overall while individual households inside it haven't been checked household-by-household — zone-level and household-level confidence are genuinely different facts, and the schema currently only models one of them.

**Recommendation:** add `data_confidence data_confidence not null default 'baseline'` and reuse the same three-value enum already defined for zones (`baseline` / `field_verified` / `due_for_reverification`) — not a new two-value household-only type — so `due_for_reverification` applies uniformly using the same 90-day threshold the design system already states (`docs/DESIGN-SYSTEM.md` §4). `last_surveyed_at` already exists and becomes the timestamp this state is computed from.

**Action:** schema change. Add the column to §5.4, note it in §7 (RLS already covers `households`, no policy change needed), and update this in the same commit as the structural-condition change since both touch `households`.

### 2.2 Zones have no GSI static-classification column — but the design explicitly needs one

TRD §8.1 requires the ML susceptibility score to be *"stored alongside GSI's static classification rather than replacing it — the two are shown together so an authority sees where the ML model agrees or disagrees with the historical-incident baseline."* `docs/DESIGN-SYSTEM.md` §5 lists a built screen — "Red zone map ... zone detail with **ML-vs-GSI divergence note**" — that depends on having both values to compare. The prototype has both: `gsi:'High', gsiPct:70` sits right next to `susp:0.91` in every zone row.

But `docs/BACKEND-SCHEMA.md` §5.3 (`zones`) only has `susceptibility_score`/`susceptibility_factors` — there is no column for GSI's own static category. Without one, the ML-vs-GSI divergence note — a named, built screen feature — has nothing on the GSI side to diverge from.

**Recommendation:** add `gsi_classification text` (or a small enum `'Low'|'Moderate'|'High'|'Very High'` matching GSI Bhusanket's own categories) and `gsi_score numeric(5,2)` (GSI's own percentage/index, distinct from the ML `susceptibility_score`) to `zones`. This is dataset-sourced (GSI Bhusanket, TRD §6 — "portal/report-based," loaded once and periodically refreshed), not computed, so it needs no `_factors` companion column.

**Action:** schema change, same commit as the above two.

*No further disagreements found beyond these six — the JSONB shapes in §6 and the RLS design in §7 were checked against the prototype's actual data shapes and match cleanly.*

---

## Part 3 — Build order

Numbering is dependency order, not calendar time — no hackathon duration was given in the docs, so phases are sized relatively (S/M/L) and marked for what can run in parallel rather than pinned to hours. **Nothing below starts until Part 1 + Part 2's six decisions are ratified by the team** — they change the enum types and two table shapes that every later phase's models, seeds, and API contracts are written against. Re-deciding them mid-build is the single most expensive mistake available here.

### Phase 0 — Foundations (S) — blocks everything

- Apply the six decisions above to `docs/BACKEND-SCHEMA.md`.
- Docker Compose skeleton: Postgres+PostGIS, Redis, MinIO, one FastAPI app container, one frontend container (TRD §14 decision 1 — one app with routers, already resolved, don't re-litigate).
- Alembic scaffold; first migration is the full corrected DDL (enums, all 16 tables including `incident_outcomes` — build the table now per CLAUDE.md even though its screen is stretch scope).
- `incident_outcomes` is pure DDL with no logic depending on it yet — free to include here rather than deferred.

**Risk:** none, if Part 1/2 are signed off promptly. All downstream risk in this plan traces back to this phase being rushed or skipped.

### Phase 1 — Data layer, auth, RLS (M) — depends on Phase 0

- Users/roles, OAuth2 password flow + JWT, per-connection `app.current_role`/`app.current_user_id` middleware.
- RLS policies on `households`, `surveys`, `zones` (rule 7).
- Seed data ported directly from the prototype's static arrays: `districts` (Dima Hasao only), `zones` ZN-01…ZN-08, `households` HH-112 etc., `shelters` SH-01 etc. — same IDs, same values, so the Python scoring port can be checked against the prototype's own numbers.

**Risk:** RLS is easy to get subtly wrong under time pressure and is exactly the kind of bug (rule 7: "a missed `WHERE` clause... must not be able to leak household vulnerability data") that doesn't show up in a demo but matters most. Write a test that logs in as `field_officer` and confirms a household outside their assigned zones returns nothing, before building anything on top — not as cleanup at the end.

### Phase 2 — Scoring engines (M) — depends on Phase 1, is the critical path

Port `vulnFactors`/`vulnScore`/`prioFactors`/`prioScore`/`prioTier`/`matchFactors`/`matchScore` to Python: same factor names, rescaled weights (§1.2 above), same thresholds. Return the `factors[]` shape from `docs/BACKEND-SCHEMA.md` §6.1 (rule 1). Not wired to endpoints yet — pure functions, unit-tested against the prototype's own seeded households/zones/shelters so the numbers match exactly.

**This is the highest-leverage phase.** Priority ranking, shelter allocation, and the dashboard's headline numbers all read these three functions — nothing past this point can be honestly demoed until this is right.

**Risk:** the rescale (§1.2) is the one place a silent, hard-to-notice bug can live — dividing the wrong thing (score instead of weights) still produces plausible-looking numbers. Test against hand-computed prototype values, not just "does it run."

### Phase 3 — Zone mapping (7.1) (M) — depends on Phase 1; data-sourcing runs in parallel with Phase 2

- Zone CRUD, `GET /zones` (paginated, `since`-aware), zone detail with incident history and the new GSI-vs-ML divergence fields (§2.2).
- Reuse `PROTOTYPE/dima-hasao-map.html`'s Leaflet setup nearly as-is for the dashboard map.
- Sourcing real GSI Bhusanket classification + the published Dima Hasao susceptibility research + IMD historical rainfall baseline for the 8 zones is a **research task, not a coding task** — start it in parallel with Phase 2, don't sequence it after. Time-box it; fall back to clearly-marked `SAMPLE DATA` (rule 6) rather than let sourcing real figures block the schedule.

**Risk:** IMD's public API access terms are unconfirmed (TRD §12/§13). Per scope discipline, the MVP's "live" IMD signal should be built against the historical baseline path from day one — don't build a hard dependency on live IMD access materializing in time.

### Phase 4 — Household assessment + priority ranking (7.2, 7.3) (S) — depends on Phase 2 + Phase 3

Wire Phase 2's `vulnScore`/`prioScore`/`prioTier` into `GET /zones/{id}/households`, a ranked-list endpoint, each returning `factors[]`. Needs Phase 3's zone `risk_score_72h` as an input to `prioFactors`, so it can't complete before Phase 3's zone rows exist (seed values are enough — the real forecasting model from Phase 10 can land later without blocking this).

### Phase 5 — Shelter allocation (7.4, 7.5) (S) — depends on Phase 2

Shelter CRUD with the `current_occupancy <= max_capacity` check already in the schema; matching endpoint wired to `matchFactors`/`matchScore`.

### Phase 6 — Logistics tracking (7.6) (M) — depends on Phase 5

`relocation_records` state machine (`assigned → in_transit → arrived`), vehicle/escort assignment. **This is also where the `audit_log` write path gets built once and reused everywhere** (rule 2) — every relocation decision and every priority-ranking write needs an audit row; build the helper here rather than bolting it onto each service separately later.

### Phase 7 — Routing (7.7) (M) — depends on nothing above; start sourcing immediately, don't sequence it

OSRM instance over the Dima Hasao OSM extract, blocked-segment penalty layer, `routes` table. TRD §13 already names the real risk here: OSM coverage for a rural, hilly district may be too sparse for sensible routes. **Verify this in week one, not right before the demo** — a manual road-graph patch is the stated fallback, and finding out it's needed late is the expensive way to find out.

### Phase 8 — Dashboard aggregation + frontend (7.8) (L) — depends on Phases 3–7 having at least stubbed endpoints

`/dashboard/summary` with `since`-based delta responses, gzip (rule 8); React dashboard consuming Phases 3–7. Frontend shell/layout/design tokens (`docs/DESIGN-SYSTEM.md`) can start much earlier, in parallel with Phase 1, against mocked API shapes — no reason a second team member waits for real endpoints to start on layout, nav, and the shared "explain this score" factors panel (design system §4).

### Phase 9 — Field survey PWA (7.10) (L) — depends on Phase 1 only; parallelizable

Survey capture form, IndexedDB/Dexie offline queue, sync endpoint doing `insert ... on conflict (survey_id) do update` (rule 5), review workflow using the corrected `approved`/`flagged` enum. Mostly independent of Phases 2–8 — good candidate for a second workstream from early on.

**Risk:** the idempotent-upsert-on-retry behavior (rule 5) is easy to get right in the happy path and wrong under an actual retried failure — test with a simulated dropped connection mid-sync, not just a clean submit.

### Phase 10 — Predictive risk forecasting (7.9) (M) — depends on Phase 3's historical rainfall baseline

XGBoost/regression 72h score with `factors[]`, one `risk_forecasts` row per zone per horizon bucket per generation cycle (not one row holding all six buckets — that's a modeling difference from the prototype's `forecastRow()` worth noting explicitly, since it changes how the ingestion job writes results). Per TRD §14, default to XGBoost over an LSTM for explainability and time.

### Phase 11 — Change detection (7.11) (S) — fully independent; good early pickup

CV differencing/thresholding on one curated before/after Sentinel pair. Zero dependency on the scoring/data-model work — needs only MinIO (Phase 0) — so it can be built by whoever's free earliest rather than waiting its turn.

### Phase 12 — Interagency handoff (7.13) (S) — depends on Phase 6 + Phase 4

`handoff_logs` CRUD + status flag surfaced on the dashboard. Low complexity; do last or fold into Phase 8.

### Phase 13 — Post-incident feedback screen (7.12) (stretch only)

The `incident_outcomes` table already exists from Phase 0. Per CLAUDE.md, build the screen only if the core loop (Phases 1–9) is genuinely done with time to spare — don't let it displace any phase above it.

---

## Summary — critical path and parallel tracks

**Critical path:** Phase 0 → 1 → 2 → 4 → 6 → 8. This is the sequence that has to be right for the demo's central claim (explainable, ranked relocation decisions) to hold up.

**Can run in parallel from early on, each needing only Phase 0/1:** Phase 7 (OSRM sourcing — start immediately, it's an infra risk not a logic dependency), Phase 9 (survey PWA), Phase 11 (change detection), and frontend shell/design-system work ahead of Phase 8.

**Where the real timeline risk sits, in order:**
1. Part 1/2 conflicts not being ratified before Phase 0 — everything downstream is written against these six decisions.
2. OSRM/OSM coverage for Dima Hasao turning out too sparse (TRD's own named risk) — verify in week one.
3. Sourcing real GSI + academic susceptibility figures taking longer than expected — time-box, fall back to labeled sample data.
4. The 0–100 → 0–1 rescale (§1.2) introducing a silent scoring bug that isn't caught until numbers are compared against the prototype directly.
5. RLS and the survey-sync idempotency guarantee (rules 5, 7) being treated as end-of-project polish instead of tested from the phase that introduces them.
