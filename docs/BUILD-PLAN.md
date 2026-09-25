# Build Plan

## Intelligent Hazard Red-Zone & Relocation Platform — SIH26191

| | |
|---|---|
| **Purpose** | Resolve the four known schema/prototype conflicts, flag two more the team missed, and set a build order for the hackathon MVP. |
| **Status** | Resolved and executed. Part 1/2's decisions were ratified and Phases 0–13 have since shipped (see commit history); kept here as the build-order record, not an open recommendation. |
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
- Seed data ported directly from the prototype's static arrays: `districts` (Dima Hasao only), `zones`, `households` HH-112 etc., `shelters` SH-01 etc. — same IDs, same values, so the Python scoring port can be checked against the prototype's own numbers. **Correction (see Phase 3 below):** only 4 of the prototype's 8 zones (`ZN-01`…`ZN-04`) were actually carried into `backend/app/seed.py`; the other 4 were never ported.

**Risk:** RLS is easy to get subtly wrong under time pressure and is exactly the kind of bug (rule 7: "a missed `WHERE` clause... must not be able to leak household vulnerability data") that doesn't show up in a demo but matters most. Write a test that logs in as `field_officer` and confirms a household outside their assigned zones returns nothing, before building anything on top — not as cleanup at the end.

### Phase 2 — Scoring engines (M) — depends on Phase 1, is the critical path

Port `vulnFactors`/`vulnScore`/`prioFactors`/`prioScore`/`prioTier`/`matchFactors`/`matchScore` to Python: same factor names, rescaled weights (§1.2 above), same thresholds. Return the `factors[]` shape from `docs/BACKEND-SCHEMA.md` §6.1 (rule 1). Not wired to endpoints yet — pure functions, unit-tested against the prototype's own seeded households/zones/shelters so the numbers match exactly.

**This is the highest-leverage phase.** Priority ranking, shelter allocation, and the dashboard's headline numbers all read these three functions — nothing past this point can be honestly demoed until this is right.

**Risk:** the rescale (§1.2) is the one place a silent, hard-to-notice bug can live — dividing the wrong thing (score instead of weights) still produces plausible-looking numbers. Test against hand-computed prototype values, not just "does it run."

### Phase 3 — Zone mapping (7.1) (M) — depends on Phase 1; data-sourcing runs in parallel with Phase 2

- Zone CRUD, `GET /zones` (paginated, `since`-aware), zone detail with incident history and the new GSI-vs-ML divergence fields (§2.2).
- Reuse `PROTOTYPE/dima-hasao-map.html`'s Leaflet setup nearly as-is for the dashboard map.
- Sourcing real GSI Bhusanket classification + the published Dima Hasao susceptibility research + IMD historical rainfall baseline for the seeded zones is a **research task, not a coding task** — start it in parallel with Phase 2, don't sequence it after. Time-box it; fall back to clearly-marked `SAMPLE DATA` (rule 6) rather than let sourcing real figures block the schedule.

**Risk:** IMD's public API access terms are unconfirmed (TRD §12/§13). Per scope discipline, the MVP's "live" IMD signal should be built against the historical baseline path from day one — don't build a hard dependency on live IMD access materializing in time.

**Phase 3 data-sourcing findings (research task, completed):**

The prototype's 8 zones (`Upper Ridge`, `Riverbend East`, `Slate Quarry`, `Mill Colony`, `Terrace Block`, `North Spur`, `Canal Fringe`, `Pine Hollow`) are synthetic constructs invented for the prototype — they are not real GSI-mapped locations, so no source gives a real classification for *them specifically*. **Only the first 4 (`ZN-01`–`ZN-04`: Upper Ridge, Riverbend East, Slate Quarry, Mill Colony) were actually carried into `backend/app/seed.py`** — this is what the live build's zone count, dashboard figures, and every downstream count in this document (11 households, 5 shelters, etc.) are built against; `Terrace Block`/`North Spur`/`Canal Fringe`/`Pine Hollow` exist only in the prototype reference and were never ported. What's real, and what isn't, about the 4 zones that were seeded breaks down as follows:

- **GSI Bhusanket** ([bhusanket.gsi.gov.in](https://bhusanket.gsi.gov.in/LS_hazard.html)) is a real, public GSI portal, but its Landslide Hazard page exposes no downloadable classification data or API — only that GSI's National Landslide Susceptibility Mapping programme uses "a semi-quantitative heuristic method per BIS guidelines" at 1:50,000 scale. No district-level GSI figures are accessible programmatically. Separately confirmed real: ASDMA signed an MoU with GSI in August 2024 to pilot a regional Landslide Early Warning System in Dima Hasao and Cachar specifically — Dima Hasao is a genuine GSI priority district, just not one with a public downloadable zonation yet.
- **The published susceptibility research TRD §8 cites is real, not fabricated** — verified: Kumar et al., *"Geospatial modelling of landslide susceptibility using modified frequency ratio, weight of evidence, and Shannon entropy: a case study in Dima Hasao district,"* Proc. Indian National Science Academy (2026), [10.1007/s43538-026-00815-w](https://link.springer.com/article/10.1007/s43538-026-00815-w). Full text is paywalled, so exact per-class area percentages weren't extractable, but the abstract confirms the frequency-ratio model performed best (success rate 0.734) and that **central and eastern Dima Hasao fall in "very high" susceptibility** — loosely consistent with, but not the source of, our sample zones' high `susceptibility_score` values, which remain sample data.
- **A real, well-documented disaster confirms the district's landslide severity**: the May 2022 Dima Hasao cluster-landslide event — 5,178 landslides, 156mm rainfall in 24h (11 May) and 540mm for the month, ~57,000 displaced, 3 deaths, New Haflong railway station buried by an ~8m-deep debris flow (Kumar et al., *Landslides* (2022), [10.1007/s10346-022-01977-6](https://link.springer.com/article/10.1007/s10346-022-01977-6); AGU Landslide Blog). This real event now replaces one of ZN-01's previously-invented `incident_history` entries in `seed.py` (district-wide attribution, not zone-specific — see the comment there).
- **IMD/CWC rainfall**: confirmed a real, likely-accessible historical baseline path exists beyond the single data.gov.in catalog page — the **National Water Data Portal** ([nwdp.nwic.gov.in](https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly)) hosts a named "Rainfall CWC Assam (1991–2020), Telemetry Hourly" dataset plus Assam Water Department manual-daily data. Whether it's bulk-download-only or has a queryable API wasn't confirmed — that's the next concrete step when Phase 10 (forecasting) needs it, not before.

**What this changes, and what it doesn't:** the district-level subdivisions our zones' `block` labels already use (Haflong, Maibang) are real; the zone geometries, populations, and most `susceptibility_score`/`gsi_classification`/`gsi_score` values are still synthetic sample data, honestly labeled as such, because no accessible source gives real per-zone figures to replace them with — inventing a precise 1:1 mapping would be worse than the current honest placeholder. Re-scoping the demo to real GSI-zone geometries or real habitations is a bigger decision than this task covers and would need the team's sign-off, not a unilateral seed-data rewrite.

### Phase 4 — Household assessment + priority ranking (7.2, 7.3) (S) — depends on Phase 2 + Phase 3

Wire Phase 2's `vulnScore`/`prioScore`/`prioTier` into `GET /zones/{id}/households`, a ranked-list endpoint, each returning `factors[]`. Needs Phase 3's zone `risk_score_72h` as an input to `prioFactors`, so it can't complete before Phase 3's zone rows exist (seed values are enough — the real forecasting model from Phase 10 can land later without blocking this).

### Phase 5 — Shelter allocation (7.4, 7.5) (S) — depends on Phase 2

Shelter CRUD with the `current_occupancy <= max_capacity` check already in the schema; matching endpoint wired to `matchFactors`/`matchScore`. Distance is a real PostGIS `ST_DistanceSphere` straight-line proxy over actual seeded geometry (§7's "designed for, not built" — real routing is Phase 7).

**Migration `0004`** later added a `standby` shelter status plus `contact_name`/`contact_phone`/`needs` columns, so the shelter officer dashboard has a real point of contact and a running needs list to show, not just occupancy — see Backend Schema §5.5.

**Found on later verification, worth flagging here rather than only in Backend Schema §5.4:** every household in a zone was seeded with that zone's centroid as its `geom`, not a distinct point — so this real distance calculation currently produces the same `distance_km`/`match_score` for every household in a given zone against a given shelter, not a genuinely household-specific number. `backend/tests/test_scoring.py`'s HH-112→SH-01 test (`distance_km=4.2`, expecting `match_score=0.90`) reflects the *prototype's* static mock figures for that pair, not what the live endpoint returns today (real seeded distance ≈1.1 km, live score ≈0.95) — the test still correctly verifies the pure scoring function, but its own comment overstates what those specific numbers represent in this build. See Backend Schema §5.4 for the full note.

### Phase 6 — Logistics tracking (7.6) (M) — depends on Phase 5

`relocation_records` state machine (`assigned → in_transit → arrived`), vehicle/escort assignment. **This is also where the `audit_log` write path gets built once and reused everywhere** (rule 2) — every relocation decision and every priority-ranking write needs an audit row; build the helper here rather than bolting it onto each service separately later.

**Migration `0005`** added `display_code`/`route_label` to `vehicles` (`VH-01`/`VH-02` trucks, `BUS-01`…`BUS-05` buses), matching the human-readable display-code convention the other entities already use — see CLAUDE.md's ID list and Backend Schema §5.7.

**"Reset demo data" (`POST /demo/seed-relocations`, `sdma_official`-only).** The Logistics Tracker's "Load demo data" button (`services/demo_seed.py`) started as a seed-once-then-no-op action; it's now a true reset on every call, because a hackathon judge re-running the demo mid-session needs the same fresh scenario each time, not whatever state the last click (or a field officer's own testing) left behind. A click deletes `relocation_records` and `surveys` (and their dependents — `handoff_logs`/`incident_outcomes` rows linked to a relocation, both FK'd with no `ON DELETE` clause so they must go first), resets `vehicles.status` back to `available` and `shelters.current_occupancy` back to `app/seed.py`'s own seeded baseline (both are fields the relocation lifecycle mutates in place, so a reset that skipped them would leave stale occupancy/status behind rows that no longer exist), then reseeds the same 5-bus / 11-household / 8-survey plan through the real allocation/status/review services — same factor snapshots and `audit_log` rows a hand-run allocation would produce. `audit_log` itself is never touched or deletable (rule 2; enforced at the grant level, not just by convention). This needed a new migration (`0006`): `app_user` had no `DELETE` grant on *any* table before this (migration `0002` only ever granted `SELECT`/`INSERT`/`UPDATE`), so the reset now has a narrowly-scoped `DELETE` grant on exactly the four tables it touches — see Backend Schema §7. The demo vehicle fleet is buses only — this platform models *pre-disaster* predictive relocation (moving households out ahead of a forecast hazard), so the seeded scenario assumes the road network is still intact; no boats/amphibious vehicles.

### Phase 7 — Routing (7.7) (M) — depends on nothing above; start sourcing immediately, don't sequence it

OSRM instance over the Dima Hasao OSM extract, blocked-segment penalty layer, `routes` table. TRD §13 already names the real risk here: OSM coverage for a rural, hilly district may be too sparse for sensible routes. **Verify this in week one, not right before the demo** — a manual road-graph patch is the stated fallback, and finding out it's needed late is the expensive way to find out.

**What got verified, and what didn't.** Queried the Overpass API live for Dima Hasao's bounding box: 2,516 tagged highway ways, including 320 trunk + 124 primary/secondary/tertiary segments — real NH27/NH627 national-highway geometry runs directly through the Haflong area (ZN-01/SH-01/SH-03). TRD's flagged coverage risk is **not** a problem for this stretch of the district; the `routes` table is seeded with one real stitched road segment (RT-07, 12.8 km, downsampled from 776 raw OSM points to ~50) rather than a synthetic straight line. What this session did *not* do: stand up the actual OSRM binary (`osrm-extract` → `osrm-partition` → `osrm-contract` over a proper `.osm.pbf`) or add it to `docker-compose.yml` — that needs a build environment with more disk/CPU headroom than this session had, and a broken/half-configured service in the default compose stack would violate TRD §4's "one-command spin-up" goal worse than not having it yet. The `routes` CRUD API, GeoJSON storage, and blocked-segment penalty layer (`POST /routes/{id}/blocked-segments`, open to any authenticated role per TRD §7.7 — a field officer reporting a landslide-blocked road shouldn't need sdma_official to do it for them) are built and real; only the routing *engine* itself (turn-by-turn shortest-path computation) remains the next concrete step, now de-risked by the coverage check above. Distance/duration in Phase 5/6's shelter-matching still use the straight-line PostGIS proxy, not this route — wiring a real route into that matching flow needs the actual OSRM engine to pick the *right* route for an arbitrary origin/destination pair, which is exactly what's still missing.

### Phase 8 — Dashboard aggregation + frontend (7.8) (L) — depends on Phases 3–7 having at least stubbed endpoints

`/dashboard/summary` with `since`-based delta responses, gzip (rule 8); React dashboard consuming Phases 3–7. Frontend shell/layout/design tokens (`docs/DESIGN-SYSTEM.md`) can start much earlier, in parallel with Phase 1, against mocked API shapes — no reason a second team member waits for real endpoints to start on layout, nav, and the shared "explain this score" factors panel (design system §4).

**Landing → sign-in → dashboard flow.** `/` (`frontend/src/pages/Landing.tsx`) is the entry point for every unauthenticated visitor regardless of which URL they hit — `RootGate` (`App.tsx`) swaps the entire authenticated route tree for the public landing page for any path nested under `/`, not just `/` itself, so a stale or bookmarked deep link never leaks past auth. Sign-in is always one modal over that page (`components/SignInModal.tsx`), never a separate route: a role-picker with all four roles (SDMA official / field officer / control room / shelter officer), where the first three share one email/password form (prefilled per seeded demo account on selection — the account behind the submitted credentials still decides the real role via `/auth/me`, picking a button doesn't) and selecting "Shelter officer" swaps those fields for a single shelter-code field and routes the submit through `ShelterAuthContext` instead — a genuinely different credential (TRD §10: a bare code, no account behind it), not just a fourth account. Clicking a role card on the landing page opens the modal pre-selected to that role (`initialRole` prop), so testing all four takes one click each rather than an extra step to pick the role inside the modal. The modal explicitly `navigate()`s on success rather than relying on `RootGate`/`ShelterRootGate`'s swap to carry it there — necessary because that swap doesn't change the URL, so without it a visitor who'd arrived at, say, `#/relocations` while logged out would land straight on that nested route post-login instead of their dashboard home. `/login`, `/shelter-login` and the old paramless `/shelter-dashboard` all still exist as routes, but only as redirects to `/`, so an old bookmark to any of them degrades gracefully instead of hitting a dead route. A successful shelter sign-in lands on `/shelter-dashboard/:code` (the server-confirmed display code, e.g. `/shelter-dashboard/SH-01`) rather than a bare `/shelter-dashboard`, so the shelter is nameable straight from the URL.

### Phase 9 — Field survey PWA (7.10) (L) — depends on Phase 1 only; parallelizable

Survey capture form, IndexedDB/Dexie offline queue, sync endpoint doing `insert ... on conflict (survey_id) do update` (rule 5), review workflow using the corrected `approved`/`flagged` enum. Mostly independent of Phases 2–8 — good candidate for a second workstream from early on.

**Risk:** the idempotent-upsert-on-retry behavior (rule 5) is easy to get right in the happy path and wrong under an actual retried failure — test with a simulated dropped connection mid-sync, not just a clean submit.

**Found and fixed on later hand-verification (a real field officer session against the deployed field PWA, not a code read):** every sync attempt failed unconditionally with `duplicate key value violates unique constraint "surveys_display_code_key"`, on every retry, not intermittently. Root cause: `next_display_code()` (`services/display_codes.py`) computed the "next" `SV-`/`HH-` number by scanning existing display codes through the caller's own request-scoped `db` session — the same session RLS applies to. A `field_officer`'s view of `surveys`/`households` is scoped to their assigned zones, so the scan systematically undercounted the true district-wide max and recomputed a code that already existed in a zone outside their assignment — on this seeded data, a field officer assigned to ZN-01/ZN-03 only sees `SV-1,2,5,6` and computes `SV-7` next, which already exists in ZN-04. Not a race condition (though the old approach was independently vulnerable to one too) — deterministic, and it broke the core field-survey submission workflow (PRD §7.10) for the exact seeded demo scenario. **Migration `0008`** replaces the scan with a real Postgres sequence per prefix (`SV`, `HH`, `HO`, `MV`, `RT` — the five prefixes that were ever auto-generated rather than caller-supplied) — sequences are schema objects, not subject to RLS, and `nextval()` is atomic regardless of concurrent callers or uncommitted rows in the same transaction, so it has neither failure mode. Verified by reproducing the exact live precondition in Docker (reset demo data, then sync as the field officer) and confirming the previously-failing request now succeeds; `tests/test_survey_sync.py` carries a permanent regression test for it.

### Phase 10 — Predictive risk forecasting (7.9) (M) — depends on Phase 3's historical rainfall baseline

XGBoost/regression 72h score with `factors[]`, one `risk_forecasts` row per zone per horizon bucket per generation cycle (not one row holding all six buckets — that's a modeling difference from the prototype's `forecastRow()` worth noting explicitly, since it changes how the ingestion job writes results). Per TRD §14, default to XGBoost over an LSTM for explainability and time.

**Migration `0007`** granted `app_user` a narrowly-scoped `DELETE` on `risk_forecasts`, so the Phase 6 demo-reset flow can clear stale forecast rows on each reseed the same way it already clears `relocation_records`/`surveys` — see Backend Schema §7.

**Found and fixed on later hand-verification (Docker, real xgboost/shap — not a doc correction, actual code changed):**

1. `ml/forecast_model.py`'s SHAP-to-score rescale divided by `base_value + shap_values.sum()` instead of `shap_values.sum()` alone, so `factors[]` contributions didn't actually sum to the score — rule 1 broken for this one endpoint despite the code's own comment claiming otherwise. Confirmed by running the trained model against all 4 seeded zones × 6 horizons in the real backend image: contributions ranged from a quarter of the score to the wrong sign. One-line fix; `tests/test_forecasts.py` now asserts the sum on every generation so this can't silently regress.
2. `seed.py`'s `zones.risk_score_72h` for all 4 zones was the prototype's *6-hour* peak value, not its 72-hour value — an exact match to `TRAINING_TARGETS_PCT[...][0]` for all four zones confirmed this wasn't noise. Corrected to the real 72h targets (0.41/0.48/0.36/0.31). Since this is `prio_score`'s highest-weighted input, the fix moved 6 of 11 seeded households down a priority tier — `tests/test_scoring.py` and `tests/test_dashboard_api.py` carry the corrected, hand-reverified expectations. See `docs/TRD.md` §8.2 for the full account.

This is exactly the class of bug Part 3's testing requirement (§1.2) exists to catch — verified by hand against a real trained model, not by trusting that a well-shaped `factors[]` array meant the numbers were right.

### Phase 11 — Change detection (7.11) (S) — fully independent; good early pickup

CV differencing/thresholding on one curated before/after Sentinel pair. Zero dependency on the scoring/data-model work — needs only MinIO (Phase 0) — so it can be built by whoever's free earliest rather than waiting its turn.

### Phase 12 — Interagency handoff (7.13) (S) — depends on Phase 6 + Phase 4

`handoff_logs` CRUD + status flag surfaced on the dashboard. Low complexity; do last or fold into Phase 8.

### Phase 13 — Post-incident feedback screen (7.12) (stretch only)

The `incident_outcomes` table already exists from Phase 0. Per CLAUDE.md, build the screen only if the core loop (Phases 1–9) is genuinely done with time to spare — don't let it displace any phase above it.

### Phase 14 — Pilot deployment (Vercel + Railway) (S) — depends on Phases 1–9 being demoable

Everything through Phase 13 had only ever run under Docker Compose on one host. This phase puts the same build in front of judges/reviewers as three separately-hosted services, without changing any application behavior — every fix below was a deployment-config or environment-portability bug, not a feature change.

- **Backend on Railway.** `railway.json` added, pointing at a new root-level `Dockerfile` (a plain `python:3.11-slim` image installing `backend/requirements.txt` — `backend/Dockerfile`'s own build context is scoped to `backend/` for docker-compose and doesn't match Railway's full-repo build). First attempt shipped with no `dockerfilePath` set, so Railway's default Dockerfile lookup at the repo root found nothing; fixed by adding the path explicitly. The start command runs `alembic upgrade head` before `uvicorn`, so a deploy migrates the database itself rather than needing a manual step afterward.
- **Managed Postgres portability.** Railway hands out a plain `postgresql://` URL and a database not named `ps191` (its own default is `railway`). Two separate bugs followed from assuming otherwise: `Settings` didn't rewrite `postgres://`/`postgresql://` to the `postgresql+psycopg://` scheme SQLAlchemy needs (psycopg2 isn't installed — only `psycopg[binary]`), and migration `0002`'s `GRANT/REVOKE ... ON DATABASE ps191` hardcoded the local Compose database name, which silently rolled back the entire migration — including the `app_user` role creation sharing that transaction — on any database with a different name. Both are fixed in `backend/app/config.py` (dynamic scheme rewrite) and `0002_display_codes_app_user_rls.py` (resolves the name via `current_database()` instead).
- **Dashboard and field PWA on Vercel.** `frontend/vercel.json` and `frontend-field/vercel.json` each pin the Vite build (`npm install && npm run build`, `dist/` output) so the two frontends deploy as separate Vercel projects rooted at `frontend/` and `frontend-field/` respectively.
- **CORS made configurable.** The backend previously allowed only the two local Vite dev origins (already flagged in its own code comment as "revisit before any real deployment" — see git history). `CORS_ALLOWED_ORIGINS`, a comma-separated Railway environment variable, now supplies the production origins (the two Vercel URLs) alongside the dev ones, with trailing slashes stripped since a browser's `Origin` header never carries one. Pointing either frontend at a new deployment is now an env var change, not a code change.

**Risk, resolved:** every bug in this phase (missing Dockerfile path, no migration-on-boot, hardcoded DB driver scheme, hardcoded DB name, hardcoded CORS origins) is a "works on my machine" class of gap that Docker Compose alone would never surface, because Compose always supplies a `postgresql+psycopg://` URL to a database actually named `ps191`. Confirms TRD §13's general point about not hard-depending on one environment's assumptions, just for infrastructure rather than an external API this time.

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
