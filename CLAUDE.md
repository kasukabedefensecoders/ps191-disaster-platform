# RAKSHAK360 — Hazard Red-Zone & Relocation Platform

Smart India Hackathon 2026, Problem Statement **SIH26191** (Ministry of Home Affairs / NDRF).
An authority-only decision and coordination layer for disaster relocation: which settlements are at risk, who lives there, where they can go, and what is stopping them getting there.

Pilot district: **Dima Hasao, Assam**.

---

## Repository layout

```
docs/          PRD.md, TRD.md, BACKEND-SCHEMA.md, DESIGN-SYSTEM.md, BUILD-PLAN.md
PROTOTYPE/     the Claude Design prototype (reference only, does not run)
```

---

## Read these before writing code

The five documents in `docs/` are the source of truth. Read the one that owns a decision rather than inferring it from code.

| Document | Authoritative for |
|---|---|
| `docs/PRD.md` | What the platform does and why. Functional requirements §7.1–§7.13, MVP vs. designed-not-built split §6, non-functional requirements §10. |
| `docs/TRD.md` | Architecture, tech stack §4, entity model §5, external API integration §6, the three genuine ML components §8, offline design §9, RBAC §10. |
| `docs/BACKEND-SCHEMA.md` | Column-level DDL, enum types, JSONB field shapes §6, row-level security §7. |
| `docs/DESIGN-SYSTEM.md` | Colour tokens (both themes), typography, interface principles, screen inventory. |
| `docs/BUILD-PLAN.md` | The conflict-resolution record (why each of the resolved conflicts below went the way it did) and the phase-by-phase build order, kept current against commit history. |

When a document and this file disagree, the document wins — say so rather than picking silently.

---

## Resolved conflicts — do not re-litigate

The Backend Schema and the prototype originally disagreed in four places. These were resolved during Phase 0 (see `docs/BUILD-PLAN.md` Part 1 for the reasoning behind each) and have shipped ever since — `docs/BACKEND-SCHEMA.md` and `backend/app/models/enums.py` agree with each other on all four:

| | Resolved value | Went with |
|---|---|---|
| Priority tier values | `immediate` / `short_term` / `medium_term` | Backend Schema |
| Score range | `numeric(5,4)`, 0–1 | Backend Schema |
| Structural condition | `Kutcha` / `Semi-pucca` / `Pucca` / `unknown` | Prototype |
| Survey review status | `unreviewed` / `approved` / `flagged` | Prototype |

Structural condition was the one that mattered most: the prototype's values are Indian construction categories a field officer in Dima Hasao would actually recognise, and they map directly onto the vulnerability weight in `vulnFactors()` — the schema's original generic labels had no such mapping. If new code or docs disagree with the table above, the table is right and the other one needs fixing, not the reverse.

---

## The working prototype

`PROTOTYPE/` holds a complete, interactive prototype of all 18 screens, built in Claude Design.

**It does not run outside Claude Design** — `PS191 Platform.dc.html` needs the `dc-runtime` in `support.js` plus React on `window`. Do not try to serve it, build it, or import from it. It is a **reference**, and a precise one.

What to take from it:

- **`PROTOTYPE/PS191 Platform.dc.html`** — the `<script type="text/x-dc">` block at the bottom holds the real scoring logic as plain JavaScript: `vulnFactors()`, `vulnScore()`, `prioFactors()`, `prioScore()`, `prioTier()`, `matchFactors()`, `matchScore()`. **Port these to Python** — same factor names, same weights, same thresholds. They are the agreed model, not a placeholder. The `<x-dc>` template above it shows every screen's layout and which fields appear where.
- **`PROTOTYPE/dima-hasao-map.html`** — working Leaflet setup: zone polygons, shelter markers, route segments with per-segment status, theme switching, and a tile-failure fallback chain. Reusable nearly as-is for the dashboard map.

Ignore `android-frame.jsx` (a device-frame mock for presenting the field app) and `support.js` (Claude Design's runtime). `.thumbnail`, `src/` and `uploads/` are export artefacts and can be deleted.

---

## Stack

Per TRD §4 — do not substitute without asking.

- **Backend:** Python 3.11, FastAPI, Uvicorn. One app with routers per service, not ten containers (TRD §14, decision 1).
- **Database:** PostgreSQL 15 + PostGIS 3, SRID 4326 throughout. Spatial from day one — no `lat`/`lng` columns.
- **Migrations:** Alembic.
- **Dashboard:** React 18 + TypeScript, Vite, Leaflet for mapping.
- **Field app:** React + Vite as a PWA, Workbox service worker, IndexedDB via Dexie.
- **Cache:** Redis. **Object storage:** MinIO locally. **Routing:** OSRM over the Dima Hasao OSM extract.
- **ML:** scikit-learn / XGBoost, GDAL + rasterio; PyTorch only for change detection.
- **Auth:** OAuth2 password flow + JWT.
- **Local run:** Docker Compose, one command.

---

## Non-negotiable rules

**1. Every score returns its factors.** Vulnerability, priority and shelter-match endpoints return a `factors[]` array — `{name, weight, input_value, contribution}` — alongside the number. The exact shape is in `docs/BACKEND-SCHEMA.md` §6.1. The frontend renders what the API sends; it never recomputes or reverse-engineers a score. This is PRD §10 and TRD Principle 3, and it is the single most important property of this system.

**2. Every ranking and relocation decision writes an `audit_log` row** capturing the actor, the action, and the factor snapshot at that moment. Append-only — no application role gets `update` or `delete` on that table.

**3. Confidence travels with the data.** Zones and households carry their verification state — `baseline`, `field_verified`, `due_for_reverification` — and the last-verified timestamp, in every response that returns them, not just detail endpoints.

**4. Unverified raises urgency.** In priority scoring, baseline-only households score *higher* than field-verified ones (a precautionary margin). This is intentional. Do not "fix" it.

**5. Offline-first is a data-model property, not a UI feature.** `surveys.survey_id` has no server-side default — the field PWA generates it client-side at capture. The sync endpoint does `insert ... on conflict (survey_id) do update`. A retried sync must never create a duplicate.

**6. Sample data is labelled as sample data.** The demo runs on seeded records. Any screen showing them keeps the `SAMPLE DATA` marker. Never present seeded figures as live government data.

**7. Roles are enforced in the database, not just the API.** Row-level security on `households`, `surveys` and `zones`, driven by `app.current_role` and `app.current_user_id` set per-connection from the JWT (Backend Schema §7). A missed `WHERE` clause in one route must not be able to leak household vulnerability data.

**8. Low-bandwidth by default.** `/dashboard/summary` takes a `since` timestamp and returns only what changed. Gzip everything. Assume a satellite-backed link, not broadband.

---

## Scope discipline

The PRD and TRD both split **built for the demo** from **designed for, not built**. Respect that split — building a "designed for" item early is how this project runs out of time.

Built: zone mapping with real GSI + published Dima Hasao susceptibility research + IMD rainfall; vulnerability and priority scoring over seeded households; shelter allocation; logistics tracking; routing with blocked segments; field survey PWA with simulated offline; the dashboard; change detection on one curated before/after image pair.

Not built (design the seam, leave the implementation): live Google Flood Forecasting polling (waitlisted — use CWC historical via data.gov.in), NDMS VSAT integration, Sachet push, live agency-to-agency handoff, continuously-polling satellite change detection, production Kubernetes deployment.

PRD §7.12 (post-incident feedback loop) has a table in the schema (`incident_outcomes`) and, as of Phase 13, a screen too (`frontend/src/pages/IncidentOutcomes.tsx`) — it was stretch scope until the core loop (Phases 1–9) was done with time to spare.

---

## Working style

- No comments in code unless something is genuinely non-obvious.
- Match the prototype's ID conventions in seed data: `ZN-01` zones, `HH-112` households, `SH-01` shelters, `MV-118` moves, `SV-4471` surveys, `HO-221` handoffs, `RT-07` routes, `VH-01`/`BUS-01` vehicles (trucks and buses get their own prefix). Primary keys themselves are UUIDs per Backend Schema §2 — these are human-readable display codes, so they need their own column.
- Before a schema change, check `docs/BACKEND-SCHEMA.md` and update it in the same commit.
- Say when something in the docs is wrong or unbuildable rather than working around it quietly.
