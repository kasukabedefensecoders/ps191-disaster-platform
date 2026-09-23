# PRODUCT REQUIREMENTS DOCUMENT

**Intelligent Hazard Red-Zone & Relocation Platform**

**Smart India Hackathon 2026 — Problem Statement SIH26191**

| Problem Statement | Intelligent Identification of Hazard-Based Red Zones, Carrying Capacity Assessment, and Immediate Relocation Needs for Vulnerable Habitations |
| --- | --- |
| PS ID | SIH26191 |
| Organization | Ministry of Home Affairs |
| Department | National Disaster Response Force (NDRF), Disaster Management Division |
| Category | Software |
| Theme | Disaster Management |
| Institution | Pillai University (PCACS), Panvel |
| Document Owner | Kasukabe Defense Coders |
| Version | 1.0 (Team approved) |
| Date | September 2026 |

## 1. Problem Statement (as issued)

India's high-risk regions face recurring natural hazards — landslides, floods, coastal erosion, and cloudbursts. Settlements in unsafe areas suffer repeated casualties and infrastructure loss. Current relocation strategies are reactive: they mobilize only after a calamity occurs, rather than anticipating and preventing it.

**Core challenge:** develop an AI-powered, GIS-integrated platform that proactively manages disaster risk through intelligent zone classification and population relocation planning.

**Expected outcomes (per PS):**

- Map and update hazard-based red zones in real time
- Evaluate the feasibility and capacity of safer alternative locations
- Rank vulnerable populations by urgency (immediate, short-term, medium-term)
- Deliver evidence-based guidance to State Disaster Management Authorities (SDMAs)

## 2. Vision

Move disaster response in vulnerable habitations from reactive to preventive: a single platform where a district authority can see, at any moment, which settlements are at risk, who lives there, where they can safely go, and what's stopping them from getting there — before the disaster occurs, not after.

The platform doesn't try to replace India's existing hazard-monitoring infrastructure (IMD, CWC, GSI, ISRO/Bhuvan, NCCR). It sits on top of it as the decision and coordination layer that turns scattered hazard data into a specific, actionable relocation plan for a specific population.

## 3. Goals

- Give SDMAs and NDRF a single dashboard that turns raw hazard data into ranked, actionable relocation decisions.
- Replace guesswork in “who moves first and where” with a transparent, explainable priority and allocation model.
- Keep the underlying risk data current through a combination of government datasets and structured field verification, rather than relying on stale, one-time surveys.
- Detect newly affected areas within hours of an active disaster, using satellite/SAR imagery, when ground access and communication are cut off.
- Be deployable on the connectivity infrastructure India's disaster-management system already has (NDMA's VSAT/satellite-phone network in vulnerable districts), not on infrastructure the team would need to build.

## 4. Target Users

| User | Role in the system |
| --- | --- |
| State/District Disaster Management Authority (SDMA) official | Primary user of the central dashboard. Views red zones, vulnerability data, shelter status, and relocation recommendations; makes and records relocation decisions. |
| NDRF field officer / surveyor | Uses the survey module to verify and update ground-level data — household counts, vulnerability factors, structural condition — for assigned zones. |
| District control room / emergency operations center | Consumes the live dashboard during an active event: affected zones, blocked routes, shelter capacity, medical/rescue needs. |

**Out of scope for this platform:** direct citizen-facing alerting and emergency communication. That problem is already addressed by NDMA's Sachet common-alerting platform; this system is built for the authorities who decide and coordinate relocation, per the PS's own framing (“deliver evidence-based guidance to State Disaster Management Authorities”). A future integration that pushes this platform's alerts into Sachet is listed as a stretch goal, not a core requirement.

**Also out of scope:** building-code/structural-safety enforcement (e.g., illegal construction audits). A location's structural condition is captured as one input to its vulnerability score, but the platform does not attempt to replace municipal building-safety enforcement, which is a separate governance problem.

## 5. User Needs

Drawn directly from how the authority user will actually work with the system:

- See a location's full profile at a glance: how many people live there, incident history, how many times a hazard has struck before, and which hazard types apply (flood, landslide, cloudburst, coastal erosion).
- Know when a location was last verified on the ground versus when it's only backed by government baseline data — a “confidence” signal, not just a static red/green marker.
- See a breakdown of who is vulnerable within a red zone — children, elderly, people needing assistance — not just a population count.
- See a computed relocation priority (immediate / short-term / medium-term) with the reasoning behind it, so it can be defended to a supervisor or the public.
- See candidate shelters for a given household, filtered and ranked by capacity, distance, and available facilities (water, medical, toilets) — not left to manually cross-reference spreadsheets.
- Get a recommended evacuation route that accounts for roads known or suspected to be blocked, especially when field officers can't reach or confirm an area directly.
- See all of the above — critical zones, affected households, shelter availability, blocked routes, medical/rescue needs — in one consolidated dashboard during an active event, instead of switching between tools.
- Get advance warning: a rolling forecast of which zones are trending toward elevated risk over the next roughly 72 hours, so relocation can be pre-staged instead of started after the fact.

## 6. Scope: MVP vs. Full Vision

#### Pilot anchor: Dima Hasao district, Assam

Dima Hasao is one of Northeast India's most consistently hazard-hit districts — recurring rainfall-triggered landslides (notably the May 2022 cluster-landslide event, which damaged the district and cut rail connectivity to the wider Northeast) combined with mountain flood risk from the same monsoon rainfall triggers. It's also one of the few Indian districts with existing peer-reviewed academic research building landslide-susceptibility models (frequency ratio, weight-of-evidence, Shannon-entropy methods) specifically for its terrain — so the team isn't starting the ML susceptibility layer (section 8) from zero; there's published methodology to build on. This isn't a one-off historical pick either: floods and landslides across Assam, Arunachal Pradesh, Mizoram, Tripura, Nagaland, Sikkim, and Meghalaya killed 30+ people as recently as June 2025, so the region is an ongoing, current risk, not a closed case study.

***Honest caveat:*** *the pilot naturally demonstrates the landslide and flood hazard paths, since that's what Dima Hasao actually faces — it's landlocked, so it won't produce live coastal-erosion or cyclone pilot data. The coastal/cyclone hazard path stays fully designed and sourced (section 8), just not demoed live from this district. State that plainly in the pitch rather than implying full four-hazard live coverage from one region.*

Hackathon judges respond well to a team that knows exactly what it can demo versus what it's designing for. Recommended split:

#### Demo-able for the hackathon (MVP)

- Red zone map for Dima Hasao district, built from GSI susceptibility data, published academic susceptibility research for the district, and IMD rainfall data as the live trigger
- Vulnerability scoring and relocation priority ranking, computed from sample household data
- Shelter capacity matching for a small, seeded set of shelters
- Field officer survey module (mobile-responsive web form is sufficient for a demo), with offline capture simulated
- Central dashboard tying the above together
- A before/after satellite image pair demonstrating the change-detection concept (not a live feed)

#### Designed for, not built for the demo

- Live polling of IMD/Google Flood Forecasting/INCOIS APIs at production scale
- True offline sync across unreliable networks
- Integration with NDMA's NDMS VSAT infrastructure
- Push integration into Sachet

## 7. Functional Requirements

### 7.1 Hazard-Based Red Zone Mapping

Maintains and displays zones classified by hazard risk, each showing: population, applicable hazard type(s), incident history (count and dates of past occurrences), and a data-confidence indicator (government-baseline vs. field-verified vs. due-for-re-verification).

### 7.2 Vulnerable Household Assessment

Captures, per household or cluster: population count, count of children/elderly/persons requiring assistance, and structural-condition flag. Rolls these up into a per-zone vulnerability score.

### 7.3 Smart Relocation Priority Ranking

Computes a priority tier — immediate, short-term, medium-term — per zone or household cluster, from combined hazard risk and vulnerability score. The ranking logic must be inspectable: an authority can see which factors drove a given ranking, not just the resulting label.

### 7.4 Shelter Suitability & Carrying Capacity

Tracks each shelter's maximum capacity, current occupancy, and available facilities (water, medical, toilets, other basic amenities), kept current as relocations occur.

### 7.5 Optimal Relocation Allocation (matching engine)

Given a household/zone needing relocation, recommends candidate shelters ranked by a combination of risk urgency, remaining shelter capacity, distance, facility match, and route accessibility.

### 7.6 Relocation Execution & Logistics Tracking

Turns an allocation decision into an actual move: assigns vehicles/transport capacity and escort personnel to each household or cluster being relocated, sequences pickups (aligned with the priority tiers from 7.3), and tracks each household's move through status states (assigned → in transit → arrived) so an authority can see not just who should move where, but whether they actually have. This is the step between “the system recommended it” and “it happened,” and it was one of the very first questions raised when this platform was scoped — it belongs alongside the allocation engine, not left implicit.

### 7.7 Safe Evacuation Route Recommendation

Recommends a route to the assigned shelter, flagging roads known or suspected to be blocked or unsafe. During an active event, blocked-road status can be informed by satellite/SAR-based change detection when ground verification isn't possible.

### 7.8 Central Disaster Management Dashboard

Single view for authorities showing: critical zones, affected households, immediate relocation needs, shelter availability/capacity, blocked routes, and outstanding medical/rescue needs. The dashboard opens on a landing/summary screen — the first thing an authority sees on login: a high-level snapshot of critical zones, active alerts, and pending relocations — before they drill into any specific zone or household. This keeps the platform authority-only in scope (no separate public-facing page) while still giving a genuine at-a-glance overview.

### 7.9 Predictive Risk Forecasting

A rolling ~72-hour risk score per zone, combining live triggering-condition data (rainfall for landslide/cloudburst risk, river levels for flood risk, cyclone/storm-surge data for coastal risk) with each zone's static hazard-susceptibility baseline, so relocation can be pre-staged ahead of the event rather than started after it.

### 7.10 Field Officer Survey Module

Field officers receive a prioritized list of zones to survey — new/unverified zones first, then zones due for scheduled or forecast-triggered re-verification. They complete a structured checklist matching the vulnerability-assessment fields (household count, elderly/children/assistance-needs count, structural condition, population), attach a photo and GPS geotag, and submit. Submissions are captured offline-first and sync when connectivity is available.

***Resolved:*** *a submitted survey updates the live map immediately, tagged “unreviewed,” with supervisor review after the fact resolving it to “approved” or “flagged” — the recommended default above, ratified in `docs/BUILD-PLAN.md` §1.4 and shipped as the `review_status` enum (Backend Schema §3) and the Survey Review screen's approve/flag actions.*

### 7.11 Satellite/SAR Rapid Damage Detection

During an active disaster, compares recent “before” imagery against new imagery (SAR preferred, since it works through cloud cover and at night) to identify newly affected areas within hours. Results are cross-referenced against the survey database so the platform reports not just where the impact is, but who is affected and what they need.

### 7.12 Post-Incident Feedback Loop

After an actual incident, ground-truth outcomes — what really happened, whether the assigned shelter was adequate, whether the route held up — are fed back into the platform to correct and sharpen the underlying risk and allocation models. This is what keeps the system's confidence-in-data signal (section 10) honest over time, rather than the models being calibrated once and left static.

### 7.13 Interagency Handoff & Coordination

Medical and rescue needs surfaced on the dashboard (7.8) aren't purely informational — each flagged need is explicitly routable to the responsible agency (NDRF ground teams, medical services, transport/logistics for section 7.6) as a recorded handoff, not just a data point the authority has to act on manually. For the hackathon MVP this can be a status flag and log; live system-to-system integration with each agency's own tools is future scope.

## 8. Data Sources & Strategy

The platform does not attempt to generate its own hazard-detection data — it consumes existing, authoritative Indian government sources and adds a field-verification and decision layer on top.

| Hazard | Live / real-time signal | Historical baseline (for red-zone marking) |
| --- | --- | --- |
| Floods | Google Flood Forecasting API (official Google–CWC partnership; live river-gauge forecasts) | CWC historical gauge records; NRSC Flood Hazard Atlas |
| Landslides | IMD live rainfall/AWS sensor data, used as the triggering signal | GSI Bhusanket susceptibility zonation; GSI historical landslide incident reports |
| Cloudburst / extreme rainfall | IMD nowcast API — district-wise warnings plus live AWS/ARG rainfall | IMD historical rainfall-vs-normal archives |
| Coastal erosion / storm surge | IMD cyclone tracking; INCOIS live storm-surge/ocean-hazard alerts | NCCR shoreline-change monitoring (since 1990); data.gov.in shoreline datasets |
| Population / vulnerability baseline | — (not a live signal) | Census/SECC data, progressively refined by field-officer surveys |
| Cross-hazard unifying layer | ISRO Bhuvan (WMS/WFS services) where a hazard layer is available | Bhuvan historical hazard layers |

**Design principle:** for landslides and coastal erosion, “live” risk isn't a dedicated real-time sensor on each red zone — it's a static susceptibility baseline (GSI, NCCR) activated by a live triggering-condition feed (IMD rainfall; IMD/INCOIS cyclone and storm-surge data). This mirrors how real early-warning systems work and is the mechanism behind the 72-hour predictive score in section 7.9.

**Where AI is actually used:** the PS calls for an “AI-powered” platform — worth being specific about what that means rather than labeling everything “AI.” Three places use genuine ML/AI, deliberately:

- **Satellite/SAR rapid damage detection (7.11):** computer-vision-based image change detection comparing before/after satellite imagery. This is established, real applied ML, not a stretch claim.
- **Predictive risk forecasting (7.9):** a trained forecasting model (e.g., regression or time-series) over rainfall, river-level, and historical-incident data producing the rolling 72-hour risk score.
- **Red-zone susceptibility refinement:** rather than treating GSI's static, historical-incident-based zones as final, apply a machine-learned susceptibility model (frequency ratio / weight-of-evidence / random forest over terrain slope, land-use change, deforestation, and rainfall history) to catch risk that pure historical pattern-matching misses. This is exactly the gap that let Irshalwadi, Maharashtra go unlisted as landslide-prone before its fatal 2023 landslide — its risk came from quarrying and deforestation, not historical incident count. For the chosen pilot, this isn't hypothetical: published academic research already builds this kind of ML susceptibility model specifically for Dima Hasao district, giving the team a real methodology to build on rather than invent from scratch.

Vulnerability scoring (7.2), priority ranking (7.3), and shelter allocation (7.5) are deliberately kept as explainable weighted-scoring and optimization/matching logic, not opaque ML — a direct consequence of the explainability requirement in section 10, not a shortfall. Stating this distinction plainly is a stronger answer to “where's the AI?” than claiming it everywhere without being able to say what it actually does.

**Access reality check:** Google's Flood Forecasting API, Bhuvan's WMS/WFS services, and data.gov.in's open API are genuinely developer-accessible and appropriate for live/on-demand integration. IMD's public API access terms (rate limits, auth) are not clearly published and should be tested early. GSI and NCCR data is portal/report-based rather than a live API — treat it as a dataset to download and periodically refresh, not something polled in real time, and represent it honestly as such in any demo or pitch.

**Explicitly rejected:** pulling incident data from social media (e.g., searching for disaster posts to infer location/impact). Verification lag defeats the purpose of “live” data, and unverified crowd-sourced claims risk spreading bad information during an actual emergency — the team considered and deliberately excluded this.

## 9. Connectivity & Resilience

The platform is authority-facing, not citizen-facing, so it does not need to build its own emergency communication or satellite-phone capability. NDMA already operates the National Disaster Management Communication Network (NDMS) — VSAT terminals and satellite phones deployed at MHA/NDMA/NDRF headquarters, all state/UT capitals, and 81 identified vulnerable districts, specifically to keep control rooms connected when terrestrial networks fail.

**Requirement:** the dashboard and field-officer sync must be designed to run over this kind of low-bandwidth, potentially satellite-backed link — lightweight payloads, offline-first data capture, graceful degradation when connectivity drops — rather than assuming always-on broadband. This is a non-functional design constraint, not a feature the team needs to build hardware for.

## 10. Non-Functional Requirements

- **Explainability:** every red-zone classification, vulnerability score, and relocation priority must show the factors behind it. Authorities acting on the system's recommendation need an audit trail, not a black-box score.
- **Offline-first:** the field survey module must capture data without connectivity and sync later without data loss or duplication.
- **Low-bandwidth operation:** dashboard and sync payloads must remain usable over constrained/satellite-backed links (see section 9).
- **Data currency & trust:** every zone shows a visible “last verified” status and source (government baseline vs. field-verified), so authorities know how much to trust a given classification.
- **Data privacy:** household-level vulnerability data (elderly, children, assistance needs) is sensitive; access should be restricted to authorized authority and field-officer roles, not publicly exposed.
- **Auditability:** relocation decisions and priority rankings should be logged for post-incident review and accountability.

## 11. Success Metrics

- Time from a live risk trigger (e.g., heavy rainfall alert) to a pre-staged relocation recommendation appearing on the dashboard.
- Percentage of red zones with field-verified (vs. government-baseline-only) data, and average data age.
- Time from a satellite-detected change to an updated affected-area assessment during an active event.
- Accuracy of shelter allocation recommendations against actual capacity/facility fit (measured in test scenarios for the demo).
- Reduction, in simulation, of manual cross-referencing time for an authority deciding “who moves where first.”

## 12. Assumptions, Constraints & Risks

- **Assumption:** government data sources (IMD, CWC/Google, GSI, NCCR, Bhuvan, data.gov.in) remain accessible at their current terms through the hackathon and any pilot phase.
- **Constraint:** GSI and NCCR data are not live APIs; the platform's “real-time” claims are limited to the hazards where a genuine live feed exists (floods, rainfall/cloudburst, cyclone/storm surge).
- **Constraint:** IMD API access terms are unverified as of this writing — architecture should not hard-depend on unconfirmed rate limits.
- **Risk:** household-level vulnerability data quality depends on field-officer survey coverage, which will be sparse at hackathon-demo scale; the demo should be explicit about which data is real vs. seeded/simulated.
- **Risk:** satellite-based change detection for rapid damage assessment is a genuinely hard technical build; for the hackathon, this should be demonstrated conceptually with a before/after image pair rather than promised as a live capability.
- **Mitigating factor:** the Dima Hasao pilot choice reduces one real risk — unlike a district picked at random, it already has published academic susceptibility-modeling research the team can reference, lowering the chance of building the ML susceptibility layer on thin or nonexistent ground-truth data.

## 13. Open Decisions for the Team

- Whether the “push to Sachet” citizen-alert integration is worth listing as a stretch goal in the pitch — a presentation call, not a build one; still open.

***Resolved:*** *pilot district is Dima Hasao, Assam (section 6).*

***Resolved:*** *field survey approval workflow — immediate update with an “unreviewed” tag, supervisor review after the fact (section 7.10).*

***Resolved:*** *interagency handoff (7.13) demo scope — `handoff_logs` CRUD plus a status flag on the dashboard is built and demoed; live agency-to-agency handoff (the actual cross-system transfer) is designed-for-but-not-built, per section 6.*

## 14. Related Documents

This PRD defines what the platform needs to do and why, for a product audience. The following documents cover how:

- **Technical Requirements Document (`docs/TRD.md`) —** architecture, tech stack (frontend/backend/database/GIS library/AI-ML approach), API integration details, system diagrams.
- **Design System (`docs/DESIGN-SYSTEM.md`) —** dashboard layouts, survey-app flow, colour tokens, screen inventory.
- **Backend Schema (`docs/BACKEND-SCHEMA.md`) —** data models for zones, households, shelters, surveys, and relocation records.
- **Build Plan (`docs/BUILD-PLAN.md`) —** the conflict-resolution record and phase-by-phase build order actually followed.
