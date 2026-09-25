# Design System

## Intelligent Hazard Red-Zone & Relocation Platform

**Smart India Hackathon 2026 — Problem Statement SIH26191**

| | |
|---|---|
| **Purpose** | Colour, typography and interface principles for every screen in the platform |
| **Status** | v3 — reverted to the full-saturation palette and three-face type system (see §1/§2.5's revision note). Tokens below are the ones actually shipping. |
| **Relates to** | PRD §7 (screen inventory), PRD §10 (explainability, data currency, privacy), TRD, Backend Schema |

---

## 1. Design Position

The platform is an authority-only decision and coordination layer, used by SDMA officials, NDRF field officers and district control rooms — often during an active event, often at night, sometimes over a satellite-backed link. The interface reads as a district control room console, not a consumer product: dark ground, dense and precise data, restrained colour so that when red appears it genuinely means danger.

This rules out several defaults. No consumer-app friendliness, no illustration, no decorative gradients, no layouts where every block is an identical rounded card. Structural devices — numbering, dividers, severity stripes — encode something true about the content rather than decorate it.

**A note on this version.** v1 of this document proposed a maximum-saturation palette (`#00043a` ground, `#ff002b`, `#00ff80`) and a three-face type system. v2 replaced it with a different, contrast-validated palette, on the reasoning that full saturation spends the danger signal everywhere at once (the argument is kept, historically, in §2.5). v3 — this version — reverts to the v1 palette and type system by explicit product decision: the team wants Deep Navy ground, Imperial Blue surfaces and Racing Red at the critical end of the risk ramp, at full saturation, and accepted the contrast trade-off that entails. Anyone extending this system should treat the tokens in §2/§3 below as canonical and re-run the contrast check in §2.5 against them before shipping a new colour.

---

## 2. Colour

Colour is expressed as CSS custom properties with a full light-theme override. No screen hardcodes a hex value in markup; severity and confidence colours resolve through the token maps in §2.3 and §2.4.

### 2.1 Ground and surfaces

| Token | Dark | Light | Role |
|---|---|---|---|
| `--bg` | `#00043a` (Deep Navy) | `#F4F6F9` | Base background |
| `--bg2` | `#002962` (Imperial Blue) | `#FFFFFF` | Nav rail, header, raised ground |
| `--panel` | `#001d4d` | `#FFFFFF` | Panels and cards |
| `--panel2` | `#002e70` | `#F4F6F9` | Nested panels |
| `--track` | `#001233` | `#E7EBF1` | Progress tracks, inert fills |
| `--rowSel` | `#003a82` | `#E8EFFB` | Selected table row |
| `--border` / `--border2` / `--borderSoft` | `#1c3f7a` / `#3868a8` / `#0a1f52` | `#DDE3EC` / `#C3CDDC` / `#EDF0F5` | Dividers, panel edges, hairlines |

Deep Navy and Imperial Blue are the two named brand anchors; `--panel`/`--panel2`/`--track`/`--rowSel` are a consistent lightness ramp built off them, not independently chosen, so panel nesting still reads as depth rather than as arbitrary variation. The light-theme column here is carried forward unchanged from v2 and remains unwired (§6).

### 2.2 Ink

| Token | Dark | Light | Role |
|---|---|---|---|
| `--ink` | `#eef1fb` | `#0F1620` | Primary text |
| `--ink2` | `#c9d3ee` | `#27313F` | Secondary text, control labels |
| `--ink3` | `#8fa0cc` | `#4C596C` | Descriptive copy |
| `--ink4` | `#7c8fc0` | `#5C6878` | Captions, column headers, metadata |
| `--ink5` | `#5870a8` | `#6B7787` | Disabled and dormant states |

### 2.3 Risk semantics

These carry meaning and are never used decoratively.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--sev1` | `#ff002b` (Racing Red) | `#D32E22` | Immediate tier, risk ≥ 80 |
| `--sev2` | `#ff5a1f` | `#D32E22` | Active alert, blocked route, risk 65–79 |
| `--sev3` | `#ffb300` | `#D98F1F` | Short-term tier, watch state, risk 45–64 |
| `--sev4` | `#a3e635` | `#C9A93A` | Medium-term tier, risk 28–44 |
| `--sev5` | `#00ff80` | `#2E8A7D` | Verified, all-clear, live status, risk < 28 |

Each severity step also carries a matched **ink** and **surface** pair (`--sev2Ink`, `--t1Bg`/`--t1Border`, `--okBg`/`--okBorder`) so a tier can be rendered as a filled chip without a per-screen contrast decision.

### 2.4 Accent, brand and domain colour

| Token | Dark | Light | Role |
|---|---|---|---|
| `--accent` | `#06BEE1` | `#2F6FE0` | Selection, focus, primary action, computed-score emphasis |
| `--brandDeep` | `#002962` (Imperial Blue) | `#2F6FE0` | Product mark |
| `--blue` | `#2541B2` | `#2F6FE0` | Informational state (in-progress, pending approval) |
| `--ocean` | `#1768AC` | `#2F6FE0` | Non-semantic data bars (factor contributions, occupancy) |

`--accent` deliberately stays a cool cyan rather than following the ground/risk colours into full saturation — selection and focus still need to read as distinct from danger, per §2.5's remaining argument on that one point.

Hazard-type colours are categorical, not severity — a flood zone is not "worse" than a landslide zone:

| Token | Dark | Light | Hazard |
|---|---|---|---|
| `--hzFlood` | `#7FB0EE` | `#2C68B8` | Flood |
| `--hzSlide` | `#C79A6B` | `#7D5530` | Landslide |
| `--hzBurst` | `#A996E8` | `#6A4FB0` | Cloudburst / extreme rainfall |
| `--hzCoast` | `#6FCFC7` | `#268888` | Coastal erosion |

### 2.5 On full saturation, and the trade-off it carries

v2 of this document argued against a full-saturation ramp: at full chroma, `#ff002b`, `#ff5a1f`/`#ff8800` and `#00ff80` compete for attention equally, so nothing reads as more urgent than anything else and the danger signal risks being spent everywhere at once. That argument still holds as a general design principle, and the reasoning is kept here rather than deleted, because it is exactly what the next person adding a colour to this ramp needs to weigh.

v3 reverts to full saturation anyway, by explicit product decision (§1). The mitigation is that `--sev1`→`--sev5` still varies **lightness and hue** together, not just chroma — Racing Red, then a red-orange, then amber, then lime, then bright green — so the progression is still legible as a sequence even at maximum saturation; it's a louder version of the same ramp shape, not five unrelated warning colours. `--accent` staying a cool cyan (§2.4) rather than joining the red end is what still keeps selection/focus distinguishable from danger under this louder palette.

The WCAG contrast validation this section previously described (`contrast()`, `textInk()`, `safeFill()` computing a 4.8:1 minimum at render time) was a property of the v2 palette's design, not of this codebase — it has not been re-run against the v3 tokens above. Whoever next touches this ramp should treat that validation as owed, not already done: full-saturation fills are more likely to fail a contrast check against light text than the muted v2 ramp was, particularly `--sev4`/`--sev5` against `--ink`.

### 2.6 Colour-blind-safe variant

An alternate tier palette (Okabe-Ito derived) is available as an appearance setting:

| Tier | Colour-blind-safe |
|---|---|
| Immediate | `#D55E00` |
| Short-term | `#E69F00` |
| Medium-term | `#56B4E9` |

**Current limitation:** this variant covers tier badges only. Continuous risk colouring (the 72-hour forecast grid, shelter occupancy bars, confidence dots) still resolves through the standard ramp, where `--sev4` and `--sev5` sit close in hue. Extending the variant to the continuous ramp is open work; until then the setting should be described as covering priority tiers, not the whole interface.

---

## 3. Typography

Three faces. v2 merged display and body into one grotesque on the reasoning that most "body" copy here is a caption or a one-line rationale, not running prose. v3 reverts to the originally-proposed three-face system: a condensed display face for headings, a serif for body copy, and mono for data — reinstated by the same product decision that reinstated the v1 palette (§1).

| Role | Face | Weights | Use |
|---|---|---|---|
| Heading | Big Shoulders Display | 400 / 600 / 700 | Screen titles, panel headings, nav labels, primary buttons |
| Body | Newsreader | 400 / 500 / 600 | Descriptive copy, rationale text, form labels, table prose values |
| Data | IBM Plex Mono | 400 / 500 / 600 | Zone and household IDs, risk scores, coordinates, timestamps, table values, status chips, column headers |

The mono face is not stylistic. It is what makes a dense table of risk scores, populations and timestamps scannable, and it signals which values came from the system rather than from prose. The division is strict: **if a value was computed or recorded by the system, it is set in mono.** Everything else is heading or body depending on whether it titles a screen/panel or describes one.

Newsreader is a text serif, not a display face — legible at body sizes but not intended for the small, dense UI chrome (badges, table column headers, compact status text) this interface is mostly made of. Where a screen has genuine running prose (a rationale paragraph, a note field, a caption), it should read in Newsreader; short interface labels inherit it as the default body face by cascade, which is an acceptable trade-off for the three-face system's sake, not a claim that Newsreader is the ideal face for a 10px badge.

Uppercase with wide tracking (`letter-spacing: .06em`–`.14em`) marks the system's own vocabulary — `IMMEDIATE`, `FIELD-VERIFIED`, `SAMPLE DATA`, `READ-ONLY SESSION`, section labels in the nav rail. It is never used for sentences.

---

## 4. Interface Principles

**Explainability is a visible component, not a promise.** Every score in the platform — household vulnerability, relocation priority, shelter match — resolves to the same four-column shape: factor name, weight, input value, contribution. One panel renders all three, with a contribution bar per factor and the tier thresholds printed below it. A new score type inherits the panel rather than getting a bespoke treatment.

**Confidence travels with the zone.** Field-verified versus government-baseline-only, and how old that verification is, is visible wherever a zone or household appears — in lists, in summary tiles, in detail panels — not only in a detail view. Three states, each with its own colour and plain-language note: `field` (verified, current), `baseline` (census/GSI only, never field-checked), `due` (verification older than the 90-day currency threshold).

**Uncertainty raises urgency, and says so.** A household with no field verification carries a precautionary margin that scores it *higher*, not lower. Because that reads backwards at a glance, the factor row states the reasoning inline rather than leaving it to be inferred.

**State reads before number.** Severity and status are encoded in form as well as value — a filled chip, a severity stripe, a rank badge — so that what needs attention surfaces on a screen that is scanned rather than read.

**Illustrative data is labelled as illustrative.** A `SAMPLE DATA` chip sits in the persistent application header, so it is present on every screen rather than on a disclaimer slide. Where a specific asset is not what it appears to be, the principle is that the caption should say so on the asset itself, not just rely on the page-level chip. Basemap geography is real; zone footprints, populations and route status are sample data, and the map captions separate the two.

**Known gap against that principle, as of this build:** the SAR change-detection screen's before/after slider (`frontend/src/components/BeforeAfterSlider.tsx`) carries only generic "BEFORE"/"AFTER" corner labels and the page-level `SAMPLE DATA` chip — no per-asset caption stating what the imagery actually is. That matters more here than elsewhere: the scene is not merely sample Dima Hasao data standing in for a real place, it's a **programmatically-generated synthetic texture** (NumPy noise plus an added patch) standing in for a satellite pass entirely — there is no real Sentinel-1 capture behind it at all (`docs/TRD.md` §8.3, `backend/app/cv/change_detection.py`). This is a real, live-app instance of the pattern rule 6 exists to prevent, not yet closed by an on-asset caption.

**Designed for constrained connectivity.** Sync state, queue depth and unreviewed status are first-class interface elements, not status-bar afterthoughts. The field module shows its own network state, what is queued on device, and what happens on reconnect — including that a retried sync upserts on a client UUID and cannot create a duplicate.

**Household detail is role-restricted.** Vulnerability data — elderly, children, assistance needs — is access-controlled at the data layer. The interface reflects the restriction: the control-room role gets its own reduced navigation, a persistent `READ-ONLY SESSION` marker, and write actions that decline with a stated reason rather than silently failing or appearing enabled.

---

## 5. Screen Inventory

Built and interactive in the prototype. Each maps to the functional requirement noted.

### Pre-authentication

| Screen | PRD § |
|---|---|
| Public landing — product framing, live district map, role overview | — |
| Authority sign-in — officer ID, password, role selection | §10 (role-restricted access) |

### SDMA official

| Screen | PRD § |
|---|---|
| Workspace home — entry point into the four working areas | §7.8 |
| Situation summary — critical zones, active alert banner, relocation and handoff counts | §7.8 |
| Red zone map — live Leaflet map, zone table with confidence chips, zone detail with ML-vs-GSI divergence note and incident history | §7.1 |
| 72-hour forecast — per-zone risk grid across six time buckets, peak value and crossing threshold | §7.9 |
| SAR change detection — before/after swipe comparison with detected-change overlay | §7.11 |
| Household assessment — per-zone household list, vulnerability score and factor breakdown | §7.2 |
| Priority ranking — ranked household list with priority factors and tier thresholds | §7.3 |
| Shelters & allocation — capacity, occupancy, facilities, match score with factor breakdown, allocate action | §7.4, §7.5 |
| Logistics tracker — assigned / in transit / arrived columns, vehicle and escort assignment, status advance | §7.6 |
| Evacuation routes — route map with per-segment status (clear / blocked / SAR-suspected) and alternative route | §7.7 |
| Survey review — field submissions with offline-capture markers, approve and flag actions | §7.10 |
| Interagency handoff — flagged needs routed to responsible agency with acknowledgement status | §7.13 |
| Field officer app — the mobile module, viewable in-frame from the authority console | §7.10 |

### NDRF field officer

| Screen | PRD § |
|---|---|
| Field home — assigned queue and sync state | §7.10 |
| Survey capture — four-step structured checklist, structure condition, photo and GPS geotag, offline/online capture | §7.10 |
| Submission history — own submissions with review status | §7.10 |
| Field officer logistics — the same relocation records the SDMA Logistics tracker shows, scoped by RLS to the officer's assigned zones, with assigned/in-transit/arrived status-advance actions | §7.6 |

### District control room

| Screen | PRD § |
|---|---|
| Situation dashboard — read-only district view: zones, relocation progress, alerts | §7.8 |

### Shelter officer — live app only, not in the prototype

A fourth role added after the prototype was frozen (`docs/BUILD-PLAN.md` Phase 8; role and auth model in `docs/TRD.md` §10). Authenticates with a bare shelter display code (e.g. `SH-01`), not an account — a deliberately weaker credential scoped only to that one shelter, never the full shelter list.

| Screen | PRD § |
|---|---|
| Shelter officer dashboard — single-shelter occupancy, facilities, contact, needs list, status, reachable at `/shelter-dashboard/:code` | §7.4 |

**Not built in the prototype:** post-incident feedback loop (§7.12) — the screen that closes the loop between what the model predicted and what actually happened, and the natural answer to *"how do you know your risk model is right?"* The prototype was frozen as a reference before this was decided; the live app added the screen in Phase 13 (`docs/BUILD-PLAN.md`) once the core loop (Phases 1–9) was done with time to spare — see `frontend/src/pages/IncidentOutcomes.tsx`.

---

## 6. Prototype Status

The full inventory above is built and interactive in `PS191_Platform.dc.html` (with `dima-hasao-map.html` for the Leaflet basemap and `android-frame.jsx` for the mobile device frame). It carries working state, not static screens: sign-in switches role and navigation, shelter allocation writes a move and updates occupancy, moves advance through their status states, surveys can be approved or flagged, handoffs dispatch, and the field module captures offline and syncs.

The basemap is real OpenStreetMap geography over Dima Hasao — Haflong, Maibang, Jatinga, Umrangso, Harangajao. Zone footprints, populations, households, shelters and route status are sample data, labelled as such in the interface.

**Known gaps, carried deliberately:**

- **Light theme is partial.** Markup is fully tokenised, but several colour maps computed in the view layer (survey review chips, handoff status chips, household source, shelter occupancy bars, logistics status, field queue priority) resolve to dark-theme hex regardless of theme. Dark is the demo default and the intended operating mode; the light override is not presentation-ready.
- **Colour-blind-safe variant covers tier badges only** (see §2.6).
- **No accessibility semantics.** All interactive elements are real buttons, but the document has no heading hierarchy, no ARIA attributes, and form labels are not programmatically associated with their inputs. This is a genuine gap for a government-facing platform and is the first thing to address past the hackathon.
- **§7.12 has no screen in the prototype** (see §5) — the live app has since added one; see §5's note.
