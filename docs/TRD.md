# Technical Requirements Document

**Intelligent Hazard Red-Zone & Relocation Platform**

*Smart India Hackathon 2026 — Problem Statement SIH26191*

| Problem Statement | Intelligent Identification of Hazard-Based Red Zones, Carrying Capacity Assessment, and Immediate Relocation Needs for Vulnerable Habitations |
| --- | --- |
| PS ID | SIH26191 |
| Organization | Ministry of Home Affairs |
| Department | National Disaster Response Force (NDRF), Disaster Management Division |
| Category | Software |
| Theme | Disaster Management |
| Institution | Pillai University (PCACS), Panvel |
| Companion document | Product Requirements Document (PRD), v1.1 — defines what and why; this document defines how |
| Document Owner | Mahasiddhi, Team Lead |
| Version | 1.0 |
| Date | September 2026 |

## Table of Contents

1. Purpose and Scope

2. Guiding Technical Principles

3. System Architecture

4. Technology Stack

5. Database & Data Model

6. External API Integration

7. Functional Requirement → Technical Component Mapping

8. AI/ML Components — Detail

9. Offline-First & Low-Bandwidth Design

10. Security, Access Control & Data Privacy

11. Deployment Architecture

12. MVP Technical Scope vs. Full Vision

13. Assumptions, Constraints & Risks (Technical)

14. Resolved Technical Decisions

15. Related Documents

## 1. Purpose and Scope

This TRD translates the approved PRD (v1.1) into a concrete, buildable technical design: system architecture, technology stack, data model, external API integration approach, the three genuine ML/AI components, and the non-functional mechanisms (explainability, offline-first sync, low-bandwidth operation, auditability) that the PRD requires.

It is scoped to match the PRD's own MVP/full-vision split (PRD §6): every choice below is marked as either built for the hackathon demo or designed for, not built — a component the architecture accommodates and the API contracts anticipate, but that is not live in the pilot build. Nothing here contradicts the PRD; where the PRD leaves an open decision (§13), this document proposes a default and flags it as such.

## 2. Guiding Technical Principles

Four decisions shape every choice in this document:

- One stack, not two. Every genuine ML/AI component in the PRD (satellite change detection, 72-hour forecasting, susceptibility refinement) is Python-native. Rather than splitting the team across a JS backend and a separate Python ML service, the backend itself is Python (FastAPI), so models are called in-process or via a thin internal queue — not a second language boundary the team has to maintain during a hackathon.
- Spatial data is a first-class citizen, not a bolt-on. Zones, households, shelters, and routes are all geometry. The database is PostGIS from day one, not a relational schema with lat/lng columns added later.
- Explainability is an API contract, not a UI afterthought. Per PRD §10, every score/priority/ranking is required to show its factors. This is enforced by having each scoring service return a factors[] array (name, weight, input value, contribution) alongside the number — the dashboard renders whatever the API sends, it doesn't reverse-engineer a black box.
- Design for the connectivity you'll actually have. Per PRD §9, the platform must run over NDMS-class VSAT/low-bandwidth links. Payload size and offline tolerance are architectural constraints checked at every layer, not a “sync feature” added to the field app alone.

## 3. System Architecture

The platform is a five-layer architecture: external data sources, an integration/ingestion layer, an application/service layer, a data layer, and a client layer, connected over a transport layer designed for constrained links (see Figure 1).

**External government data sources.**

IMD (rainfall/nowcast), CWC/Google Flood Forecasting API, GSI Bhusanket, INCOIS, NCCR, ISRO Bhuvan, and Sentinel SAR/optical imagery — consumed as-is, per PRD §8. The platform generates none of this data itself.

**Integration & ingestion layer.**

A set of scheduled connectors, one per source, each with its own polling cadence, retry/backoff policy, and a normalizer that maps the source's native format into an internal hazard-event schema. Both the raw payload and the normalized event are persisted — raw for audit/debugging, normalized for everything downstream. This isolates the rest of the system from any one source's quirks (GSI/NCCR being portal-based rather than API-based, IMD's unconfirmed rate limits, etc. — PRD §12).

**Application/service layer.**

One FastAPI app, one process, with a router per PRD functional requirement or closely related pair (mapped in full in §7 — 14 routers as of the current build: zones, households, shelters, vehicles, escorts, relocations, routes, dashboard, surveys, forecasts, change_detection, handoffs, incident_outcomes, demo, plus auth). This is the resolved form of decision 1 in §14 below — drawn so a router could later move behind its own service without an API contract change, but nothing is split into separate services today; there is no inter-service REST traffic to speak of.

**Data layer.**

PostgreSQL + PostGIS as the system of record; object storage for imagery and survey photos; Redis for caching and live-feed buffering; an append-only audit log table for relocation decisions and priority rankings (PRD §10, auditability).

**Client layer.**

A React dashboard for SDMA officials/control room, and a separate installable web app (PWA) for field officers, built offline-first.

**Transport.**

HTTPS/REST with JSON payloads, gzip-compressed, designed to degrade gracefully on NDMS-class satellite/VSAT links (PRD §9) rather than assuming always-on broadband.

![Figure 1 — System Architecture](figures/figure-1-system-architecture.png)

*Figure 1 — System Architecture*

## 4. Technology Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Central dashboard (frontend) | React 18 + TypeScript, Vite build | Fast hackathon iteration; large ecosystem; TypeScript catches integration bugs across a multi-person team under time pressure |
| Mapping (dashboard) | Leaflet.js + GeoJSON, with direct WMS/WFS layer support | Open-source, no license/API-key friction during a hackathon; consumes Bhuvan's WMS/WFS layers (PRD §8) directly |
| Field survey app | React + Vite, packaged as a PWA (Workbox service worker) | One codebase, installable on field officers' phones without an app-store build; service worker enables offline-first (§9) in the demo timeframe |
| Offline client storage | IndexedDB (via Dexie.js) | Structured local storage for queued survey submissions and cached zone/shelter data, with a defined schema for delta-sync |
| Backend API | Python 3.11 + FastAPI + Uvicorn | Async, auto-generated OpenAPI docs, and the same language as every ML component — see Principle 1 |
| Database | PostgreSQL 15 + PostGIS 3 | Spatial queries (point-in-polygon, distance/nearest-shelter, route geometry) are core to almost every requirement |
| Cache / live-feed buffer | Redis | Caches polled hazard feeds between ingestion cycles; backs the offline-sync queue's server side |
| Object storage | S3-compatible bucket (MinIO for demo; AWS S3 / NIC MeghRaj for hosted deployment) | Satellite imagery tiles and survey photos don't belong in the relational DB |
| Routing engine | OSRM over OpenStreetMap road network for Dima Hasao district | Open, self-hostable, fast; supports a custom blocked-segment penalty layer for §7.7 |
| ML — susceptibility refinement & forecasting | scikit-learn / XGBoost, GDAL + rasterio for terrain derivatives | Matches the published frequency-ratio / weight-of-evidence / random-forest methodology already available for Dima Hasao |
| ML/CV — satellite change detection | PyTorch + rasterio/OpenCV; differencing/thresholding baseline, Siamese U-Net as stretch | Reflects the PRD's honesty about this being demoed conceptually via a before/after pair |
| Auth | OAuth2 password flow + JWT (FastAPI security utilities) | Standard, fast to implement, supports role-based access (PRD §10) |
| Containerization / demo deployment | Docker Compose (frontend, services, Postgres+PostGIS, Redis, MinIO, OSRM) | One-command spin-up for judges/reviewers; mirrors production composition |
| CI | GitHub Actions (lint + test on push) | Keeps a multi-person student team from breaking each other's services during crunch |
| Designed for, not built — production hosting | Government cloud (NIC MeghRaj) or on-prem near an NDMS point of presence | Matches PRD §9's low-bandwidth/VSAT constraint |
| Designed for, not built — production messaging | MQTT or a managed queue (e.g., SQS) for survey-sync and interagency handoff at scale | REST + IndexedDB queueing suffices at hackathon/pilot scale; a queue matters as officer count and event volume grow |

## 5. Database & Data Model

PostGIS is used for every table with a spatial dimension. Below are the core entities; exact column-level DDL belongs in the separate Backend Schema Document (PRD §14), but the shape is fixed here so the API contracts in §7 are stable.

| Entity | Key fields | Notes |
| --- | --- | --- |
| zones | zone_id, geom (POLYGON), hazard_types[], population, incident_history (JSONB), data_confidence, last_verified_at, susceptibility_score, risk_score_72h | One row per red zone; §7.1, §7.9 |
| households | household_id, zone_id (FK), geom (POINT), population_count, children_count, elderly_count, assistance_needs_count, structural_condition, vulnerability_score | §7.2 |
| shelters | shelter_id, geom (POINT), max_capacity, current_occupancy, facilities (JSONB), status | §7.4 |
| surveys | survey_id, zone_id (FK), officer_id (FK), submitted_at, payload (JSONB), photo_url, geotag (POINT), review_status | Offline-captured, synced; §7.10 |
| relocation_records | record_id, household_id (FK), shelter_id (FK), priority_tier, route_id (FK), status, vehicle_id, escort_id, timestamps | §7.5, §7.6 |
| routes | route_id, origin_geom, dest_geom, path (LINESTRING), blocked_segments (JSONB), updated_at | §7.7 |
| risk_forecasts | forecast_id, zone_id (FK), horizon_hours, score, factors (JSONB), generated_at | Rolling 72h score; §7.9 |
| change_detections | detection_id, zone_id (FK), before_image_ref, after_image_ref, detected_at, affected_area_geom, cross_referenced_survey_ids[] | §7.11 |
| handoff_logs | log_id, need_type, agency, status, linked_record_id, timestamps | §7.13 |
| audit_log | entry_id, actor_id, action_type, entity_ref, factors_snapshot (JSONB), created_at | Immutable, append-only; PRD §10 |
| users | user_id, role, district_id, auth fields | RBAC per PRD §10 |

Every scoring/ranking table (zones.susceptibility_score, households.vulnerability_score, risk_forecasts.factors) stores its factor breakdown alongside the number, not just the final value — this is what makes the explainability requirement (PRD §10) a data-model guarantee rather than a UI promise.

Five more tables were added at the schema layer once column-level design started — `districts`, `vehicles`, `escorts`, `user_zone_assignments`, and `incident_outcomes` — each called out and justified individually in Backend Schema §1; this list stays the fixed entity-level shape referenced above, not a mirror of every table.

## 6. External API Integration

| Source | Signal | Access pattern | Auth / access notes | Fallback if unavailable |
| --- | --- | --- | --- | --- |
| Google Flood Forecasting API | Live river-gauge forecasts | Scheduled poll (hourly) — production only | Free, but a limited pilot: waitlist access, Google's own docs say approval can take months — not usable in a hackathon timeline | Primary source for the hackathon: CWC historical data via data.gov.in (free, immediate). Google API applied for in parallel as a future upgrade, not depended on |
| IMD rainfall/AWS/nowcast | Live rainfall trigger | Scheduled poll (sub-hourly) | Access terms unconfirmed — verify early | Historical rainfall-vs-normal baseline, flagged degraded |
| GSI Bhusanket | Susceptibility zonation, incidents | One-time + periodic refresh | Portal/report-based | N/A — dataset, not live |
| INCOIS | Cyclone / storm-surge alerts | Scheduled poll | Public alerts | Fall back to IMD cyclone tracking |
| NCCR | Shoreline-change monitoring | One-time + periodic refresh | Portal/report-based | N/A — dataset, not live |
| ISRO Bhuvan | WMS/WFS hazard layers | On-demand fetch | Developer-accessible | Cache last-fetched tiles client-side |
| data.gov.in | Shoreline / open datasets | One-time download | Open API | N/A |
| Sentinel SAR / optical | Before/after imagery | On-demand (demo); event-triggered in production | Free tier, registration required | Demo uses a pre-selected before/after pair |

Every connector in the integration layer (§3) implements the same interface — poll() → raw_payload, normalize(raw_payload) → hazard_event — so a source that turns out to be rate-limited or flaky (the IMD risk called out in PRD §12) is isolated to one connector, not a system-wide failure.

**Verified access reality.**

Every source in this table is free — none of them are paid services, and no team budget is required anywhere in this architecture. The one genuine access blocker is Google's Flood Forecasting API pilot waitlist (above), which is a timing problem, not a cost problem, and is designed around rather than depended on. IMD's access terms remain undocumented publicly as of this writing; the team should register early and treat the historical rainfall baseline as the safe default rather than assume live access will arrive in time for the hackathon.

## 7. Functional Requirement → Technical Component Mapping

| PRD § | Requirement | Owning service | Key mechanism |
| --- | --- | --- | --- |
| 7.1 | Hazard-based red-zone mapping | Zone & Red-Zone Service | PostGIS polygon store + data-confidence field |
| 7.2 | Vulnerable household assessment | Vulnerability & Priority Engine | Weighted scoring over household fields (explainable, not ML) |
| 7.3 | Smart relocation priority ranking | Vulnerability & Priority Engine | Combines hazard risk + vulnerability score into a tier, with factors[] |
| 7.4 | Shelter suitability & carrying capacity | Shelter & Allocation Engine | Live capacity/occupancy tracking, PostGIS distance queries |
| 7.5 | Optimal relocation allocation | Shelter & Allocation Engine | Weighted matching (urgency, capacity, distance, facility, route access) |
| 7.6 | Relocation execution & logistics tracking | Logistics & Relocation Tracker | State machine (assigned → in_transit → arrived) |
| 7.7 | Safe evacuation route recommendation | Routing Service | OSRM + blocked-segment penalty layer |
| 7.8 | Central disaster management dashboard | Dashboard frontend + aggregation endpoint | /dashboard/summary composes zones, households, shelters, routes, handoffs |
| 7.9 | Predictive risk forecasting | Forecasting Service | XGBoost/regression → 72h rolling score |
| 7.10 | Field officer survey module | Survey Service + Field PWA | Offline-first capture, prioritized queue, delta-sync, unreviewed tag |
| 7.11 | Satellite/SAR rapid damage detection | Change-Detection Service | CV differencing/thresholding, cross-referenced against surveys |
| 7.12 | Post-incident feedback loop | Forecasting Service + Allocation Engine retraining | Ground-truth outcomes stored, periodic retraining job |
| 7.13 | Interagency handoff & coordination | Handoff Log service | Status-flag + log; not a live agency integration for the MVP |

## 8. AI/ML Components — Detail

The PRD is explicit (§8) that only three components are genuine ML, and that everything else is deliberately explainable rules/optimization logic. This section gives each of the three a concrete pipeline.

### 8.1 Red-Zone Susceptibility Refinement

Features: terrain slope and aspect (derived from SRTM DEM via GDAL/rasterio), land-use change (from multi-year satellite composites), deforestation indicators, and historical rainfall. Model: frequency ratio / weight-of-evidence as a baseline (matching the published Dima Hasao academic methodology referenced in PRD §6/§8), with a random-forest classifier as a comparison model. Output: a susceptibility score per zone, stored alongside GSI's static classification rather than replacing it — the two are shown together so an authority sees where the ML model agrees or disagrees with the historical-incident baseline (directly addressing the Irshalwadi gap named in PRD §8).

### 8.2 Predictive Risk Forecasting (72-Hour Rolling Score)

Features: live rainfall (IMD), river-gauge levels (CWC/Google), cyclone/storm-surge indicators (INCOIS), each zone's static susceptibility baseline. Model: gradient-boosted trees (XGBoost) or a simple LSTM if time-series structure is needed, trained on historical hazard-event outcomes for the pilot district. Output: a score and a factors[] breakdown per zone, refreshed on each ingestion cycle, feeding the dashboard's forecast view (PRD §5).

### 8.3 Satellite/SAR Rapid Damage Detection

Input: a before/after image pair (SAR preferred for cloud/night robustness). Baseline method: pixel-level differencing + thresholding on radar backscatter change; stretch goal: a Siamese U-Net trained on labeled change-detection datasets if time allows. Output: an affected-area polygon, cross-referenced against households/surveys to answer not just “where” but “who.” For the hackathon, this is demonstrated with one curated before/after pair rather than a live feed (PRD §12) — the pipeline code is real, the input is fixed.

**On feasibility and access.**

The Sentinel/Copernicus imagery this component runs on is free and openly accessible to anyone, anywhere, with no government relationship, fee, or special permission required — including a student hackathon team. This is a deliberate reason Sentinel was chosen over ISRO's own satellite catalog for this component. What is not feasible for any hackathon team — not as a skill gap, but as a structural constraint — is a live, continuously-polling system that automatically detects change the moment a new satellite pass occurs; that requires production-scale cloud infrastructure watching global satellite feeds around the clock, which no team builds in a hackathon window. The distinction that matters when presenting this to judges: the algorithm and the imagery are both genuinely real and running; only the “triggers automatically, all the time” part is future/production scope.

### 8.4 Retraining Loop

Per PRD §7.12, ground-truth outcomes (shelter adequacy, route reliability, actual vs. predicted impact) are captured post-incident and stored. For the hackathon this is a scheduled batch job design (not a live continuous-learning system) — retraining is triggered manually or on a fixed cadence, an honest match to how infrequently a real incident actually generates ground truth.

![Figure 2 — End-to-End Data Flow: Live Hazard Trigger → Relocation → Feedback](figures/figure-2-end-to-end-data-flow-live-hazard-trigger-relocation-feedback.png)

*Figure 2 — End-to-End Data Flow: Live Hazard Trigger → Relocation → Feedback*

## 9. Offline-First & Low-Bandwidth Design

Per PRD §9 and §10, the field survey module and the dashboard sync must tolerate NDMS-class VSAT/satellite-backed connectivity, not assume broadband.

**Field survey module.**

Submissions are written to IndexedDB immediately on capture (photo + GPS geotag + form fields), independent of network state. A background sync (Workbox BackgroundSync) queues each submission and retries with exponential backoff. Each submission carries a client-generated UUID so a retried sync after a partial failure doesn't create a duplicate record — the server upserts by that UUID rather than inserting blindly.

**Conflict handling.**

Since a single field officer owns a given survey submission, conflicts are rare by design; the default policy is last-write-wins on the submission itself, with the “unreviewed” review-status tag (§7.10) as the actual safeguard against bad data reaching the live map — a supervisor, not a merge algorithm, resolves disputed data.

**Dashboard payloads.**

The /dashboard/summary endpoint (§7.8) is deliberately not “return everything” — it returns only what changed since the client's last successful poll (a since timestamp parameter), keeping payloads small on a constrained link. Map tiles from Bhuvan's WMS are cached client-side after first fetch rather than re-requested every session.

**Designed for, not built:**

true multi-day offline operation and conflict resolution across many concurrent officers in the same zone. The hackathon demo simulates offline capture by toggling network access in the browser rather than testing against an actual satellite link.

**On NDMS specifically.**

The VSAT/satellite network referenced above (NDMS) is existing infrastructure already owned and operated by NDMA — this design targets compatibility with it; it does not require the team to obtain access to it, and no request to any government body is implied or needed. The hackathon demo uses no satellite hardware or government network of any kind — low-bandwidth behavior is demonstrated entirely by throttling the demo's own network connection. If the platform were ever adopted for real deployment, it would run on connectivity the government already owns and operates; this design does not imply or require any new government investment or approval.

## 10. Security, Access Control & Data Privacy

Per PRD §10, household-level vulnerability data is sensitive and access must be restricted to authorized roles.

- Roles: sdma_official (full dashboard access, can confirm relocation decisions), field_officer (survey submission, read-only zone data for assigned zones), control_room (read-only dashboard access during active events).
- Auth: JWT-based, issued on login, short-lived access token + refresh token, scoped by role and (for field officers) by assigned district/zone set.
- Transport security: TLS for all API traffic, including over the low-bandwidth transport path.
- Data at rest: household-level fields (children/elderly/assistance-needs counts) are stored in the same database as everything else but are excluded from any API response the field_officer role can query outside their assigned zones.
- Auditability: every relocation decision and priority ranking write also writes an audit_log row capturing the actor, the action, and the factor snapshot at that moment — this is what makes a ranking “defensible to a supervisor or the public” (PRD §5) after the fact, not just at the moment it was shown.
- Shelter officer sessions (the shelter officer dashboard's code-based login, `POST /auth/shelter-login`) are a deliberately separate, lower-trust credential from the three roles above: a shelter officer authenticates with just their shelter's own display code (e.g. `SH-01`), not an account. The resulting token isn't scoped by `role`/`user_id` the way households/zones/surveys are (Backend Schema §7) — it's scoped by construction, since it only ever unlocks `GET`/`PATCH /shelters/me` for the one shelter whose code was presented, never the full shelter list or any other endpoint. This is proportionate to what the token protects (occupancy, facilities, needs, status on a single shelter — no household-level PII) but is a materially weaker credential than a JWT issued through `/auth/login`, so it should not be extended to guard anything more sensitive without revisiting this design.

## 11. Deployment Architecture

**Hackathon demo:**

Docker Compose on a single host — the frontend, one consolidated FastAPI app with routers (§3, §14 decision 1), Postgres+PostGIS, Redis, MinIO, and a self-hosted OSRM instance pre-built for the Dima Hasao road network extract.

**Designed for, not built — production:**

containers on Kubernetes (or the equivalent managed service on NIC MeghRaj, India's government cloud), placed close to an NDMS point of presence to minimize hop count over the constrained link (PRD §9). Horizontal scaling applies to the FastAPI app; if a router later needs to scale independently of the rest, that's the point at which it would move behind its own service (§3). PostGIS scales vertically first, with read replicas for the dashboard's read-heavy queries if district count grows beyond the pilot.

## 12. MVP Technical Scope vs. Full Vision

Mirroring PRD §6:

**Built for the hackathon demo:**

Zone & Red-Zone Service with real GSI + published Dima Hasao susceptibility research + live IMD rainfall polling; Vulnerability & Priority Engine and Shelter & Allocation Engine over seeded household/shelter data; Field Survey PWA with simulated offline capture; Central Dashboard with landing/summary screen; susceptibility-refinement and forecasting models trained on available historical data for the pilot district; change detection demonstrated on one curated before/after image pair.

**Designed for, not built for the demo:**

production-scale polling of IMD/Google/INCOIS APIs (the demo uses CWC/data.gov.in historical data as the flood signal, not Google's waitlisted live API — §6); true offline sync tested over an actual constrained link; NDMS VSAT integration (a compatibility target, not something the team requests access to — §9); push integration into Sachet; live interagency system-to-system handoff (7.13 stays a status flag + log for the MVP); continuously-polling live satellite change detection (§8.3 — no hackathon team builds this; the demo runs the real algorithm on one real, pre-downloaded image pair).

## 13. Assumptions, Constraints & Risks (Technical)

- Assumption: the government data sources listed in §6 remain accessible on their current terms through the hackathon and pilot phase (same as PRD §12). None of them are paid services — the entire architecture requires no team budget.
- Resolved risk: Google's Flood Forecasting API is free but a limited pilot with a multi-month waitlist, confirmed from Google's own documentation — not usable within a hackathon timeline. The team applies for it in parallel as a future upgrade path, but the demo and MVP rely on CWC historical data via data.gov.in instead, which is free and available immediately (§6).
- Constraint: GSI and NCCR are not live APIs — the ingestion layer treats them as periodically-refreshed datasets, not polled sources.
- Constraint: IMD's API access terms (rate limits, auth) are unverified as of this writing; the forecasting pipeline is built to degrade to the historical baseline rather than fail if IMD access turns out to be more restricted than expected.
- Resolved risk: a many-service split would have been too much surface area for a hackathon team to stand up and integrate in the available time; the build went with a single FastAPI app with a router per functional area sharing one process (§3, §14 decision 1), preserving API contracts so a future split behind its own service remains possible without a rewrite.
- Risk: OSRM's road-network extract for Dima Hasao may be sparse in OpenStreetMap coverage for a rural, hilly district; this should be verified early, with a manual road-graph patch as a fallback if OSM coverage is too thin to produce sensible routes.
- Risk: training data for the susceptibility and forecasting models is limited to what the published Dima Hasao research and available historical records provide; model outputs for the demo should be presented with that caveat rather than overstated confidence.

## 14. Resolved Technical Decisions

All four decisions below were open at design time and have since been ratified and built; kept here as the record of what was decided and why, not as open items.

1. **Service granularity: one FastAPI app with routers, not separate containers per service** (§3, §11, §13). Confirmed in `backend/app/main.py`, currently 14 routers plus auth sharing one process. Split a router into its own service only if it later needs independent scaling.
2. **Survey approval workflow: the PRD's recommended default** (§7.10) — immediate update with an “unreviewed” tag, resolved to “approved”/“flagged” on supervisor review. Shipped as the `review_status` enum (Backend Schema §3) and the Survey Review screen's approve/flag actions.
3. **Forecasting model: XGBoost**, not an LSTM, for explainability and time (PRD §10). Shipped in Phase 10 (`docs/BUILD-PLAN.md`) with real per-prediction SHAP factor contributions — see `backend/app/services/forecasts.py`.
4. **Change detection: the differencing/thresholding baseline, not the Siamese U-Net.** Shipped in Phase 11 as CV differencing/thresholding on one curated before/after Sentinel pair (`docs/BUILD-PLAN.md`); the U-Net remains designed-for-not-built stretch scope, unstarted.

## 15. Related Documents

- Product Requirements Document (`docs/PRD.md`) — v1.1, defines the what and why this document implements.
- Design System (`docs/DESIGN-SYSTEM.md`) — dashboard layouts, survey-app flow, colour tokens, screen inventory.
- Backend Schema (`docs/BACKEND-SCHEMA.md`) — full column-level data models for zones, households, shelters, surveys, and relocation records; §5 of this document gives the entity-level shape it formalizes.
- Build Plan (`docs/BUILD-PLAN.md`) — the conflict-resolution record behind §14 above and the phase-by-phase build order actually followed.
