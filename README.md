# PS191 — Hazard Red-Zone & Relocation Platform

Smart India Hackathon 2026, Problem Statement **SIH26191** (Ministry of Home Affairs / NDRF).

An authority-only decision and coordination layer for disaster relocation: which settlements are at risk, who lives there, where they can go, and what is stopping them getting there. Pilot district: **Dima Hasao, Assam**.

Full requirements, architecture, schema and design docs live in [`docs/`](docs/). Contributor instructions (repo layout, stack, non-negotiable rules) live in [`CLAUDE.md`](CLAUDE.md) — read that before making changes.

## Live deployment

The pilot build also runs as three separately-hosted services (see [`docs/TRD.md`](docs/TRD.md) §11 for how) — no local setup needed to look at it:

- **Backend API (Railway):** https://ps191-disaster-platform-production.up.railway.app/docs
- **Main app** — SDMA official / field officer / shelter officer / control room dashboards (Vercel): https://ps191-disaster-platform.vercel.app
- **Field survey PWA** (Vercel): https://ps191-field-app.vercel.app

This deployment has no Redis, MinIO or OSRM instance behind it (see TRD §11's "known gaps" note) — routing, object storage and live-feed caching remain local-Compose-only for now.

## Stack

- **Backend:** Python 3.11, FastAPI, PostgreSQL 15 + PostGIS 3, Alembic, Redis, MinIO.
- **Dashboard:** React 18 + TypeScript, Vite, Leaflet.
- **Field app:** React + Vite PWA, Dexie (IndexedDB), Workbox service worker.

See [`docs/TRD.md`](docs/TRD.md) §4 for the full rationale.

## Quickstart

Everything runs via Docker Compose — you do not need Python, Node or Postgres installed locally.

```bash
docker compose up -d
```

This starts Postgres/PostGIS, Redis, MinIO, the FastAPI backend (`:8000`), the SDMA/field-officer dashboard (`:5173`) and the field survey PWA (`:5174`). The first run still needs two one-off setup steps against the backend container, since migrations and seed data are deliberate steps, not baked into the image:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

`app.seed` populates one district (Dima Hasao), 4 zones, 11 households, 5 shelters, 7 vehicles, 2 escorts, 1 route and 3 demo user accounts — see [`backend/app/seed.py`](backend/app/seed.py) for the exact figures, all clearly marked `SAMPLE DATA` (never presented as live government data — CLAUDE.md rule 6).

Open **http://localhost:5173** — you land on the public landing page first (map, hero copy, role descriptions), not a login form. Sign in from there.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| SDMA official (full access) | `sdma.official@ps191.dev` | `ps191-demo-pass` |
| Field officer (survey only) | `field.officer@ps191.dev` | `ps191-demo-pass` |
| Control room (read-only) | `control.room@ps191.dev` | `ps191-demo-pass` |

The sign-in modal's SDMA/FIELD/CONTROL buttons prefill these — picking one doesn't fake a role; the account behind the submitted credentials still decides the real role via `/auth/me`.

**Shelter officer** sign-in is a fourth option in the same sign-in modal (select "SHELTER"), but a lighter credential than the other three: no account, just the shelter's own display code (e.g. `SH-01`) — see [`docs/TRD.md`](docs/TRD.md) §10.

## Landing → sign-in → dashboard flow

`/` is the entry point for every unauthenticated visitor, on any URL — a stale or bookmarked deep link (e.g. `/#/relocations`) still resolves to the landing page, never a nested authenticated route, until you're actually signed in. Sign-in is a modal over that page, not a separate page you navigate to: the landing page (hero, map, role cards) stays visible underneath, and closing the loop, a successful sign-in routes you straight to your role's dashboard home — never an intermediate page.

## Testing with demo data

The **Logistics tracker** screen (signed in as the SDMA official) has a **"Reset demo data"** button. Click it any time you want the system back to a known, fresh state for a demo or a test pass:

- Deletes every `relocation_record` and `survey`, plus their dependents (`handoff_logs`/`incident_outcomes` linked to a relocation).
- Resets vehicle status back to `available` and shelter occupancy back to its seeded baseline — the two fields a relocation's lifecycle mutates in place.
- Reseeds the same fixed scenario: 5 buses carrying all 11 households across varying stages (in transit / assigned / arrived), and 8 re-verification surveys (half reviewed, half not) — through the same allocation/status/review services a real decision would use, so the reseeded rows carry real factor snapshots and `audit_log` entries, not raw inserts.
- Never touches `districts`/`zones`/`households`/`shelters`/`vehicles`/`users` themselves, and never touches `audit_log` (append-only, enforced at the database grant level — see [`docs/BACKEND-SCHEMA.md`](docs/BACKEND-SCHEMA.md) §7).

Safe to click repeatedly — each call fully resets before reseeding, so a judge re-running the demo mid-session always lands on the same scenario. Try it signed in as each role in turn (SDMA official vs. field officer) to see the same underlying data scoped differently: a field officer's dashboard and zone map are restricted to their assigned zones via row-level security, not just a frontend filter.

## Running tests

```bash
docker compose exec backend python -m pytest
```

## Resolved conflicts between the backend schema and the prototype

The Backend Schema and the original Claude Design prototype originally disagreed on four enum shapes (priority tier values, score ranges, structural condition labels, survey review status). These were resolved in Phase 0 and have shipped ever since — `docs/BACKEND-SCHEMA.md` and `backend/app/models/enums.py` agree with each other on all four. See [`CLAUDE.md`](CLAUDE.md#resolved-conflicts--do-not-re-litigate) for the resolved values and [`docs/BUILD-PLAN.md`](docs/BUILD-PLAN.md) Part 1 for the reasoning behind each.
