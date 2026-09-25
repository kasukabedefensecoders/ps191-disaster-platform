import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import Escort, Household, Shelter, Survey, User, Vehicle, Zone
from ..schemas.demo import DemoSeedResponse
from ..schemas.relocation import RelocationRecordCreate
from ..seed import SHELTERS as SEED_SHELTERS
from ..seed import ZONES as SEED_ZONES
from . import relocations as relocations_service
from .change_detection import ensure_sample_imagery_for_zone
from .display_codes import next_display_code

# Change 4's "Load Demo Data" button. Judge-facing, so it's a true reset on
# every click rather than the seed-once-then-no-op behaviour an earlier
# version of this had: a judge re-running the demo mid-session needs the
# same fresh scenario every time, not whatever state the last click (or a
# field officer's own testing) left behind. Driven by the real allocation/
# status/review services (not raw inserts) so the reseeded rows carry real
# factor snapshots, audit_log rows, and arrival side-effects the same as a
# hand-run allocation or review would.
#
# Only demo-generated state is touched: relocation_records, surveys,
# risk_forecasts, change_detections, and the fields their own lifecycles mutate in place
# (vehicle.status, shelter.current_occupancy, zones.risk_score_72h/
# risk_score_factors) get reset to their app.seed baseline.
# districts/zones/households/shelters/vehicles/users themselves are never
# *reseeded* here (their own rows are never dropped/recreated) — if that's
# needed too, that's backend/app/seed.py's job. audit_log is never touched
# (rule 2 — append-only; the DB itself revokes update/delete on it from the
# app role, so a past demo run's audit trail survives every reset).

# vehicle display_code, shelter display_code, target status, household
# display codes riding that vehicle — the bus-consolidation scenario
# (Change 3): several households sharing one vehicle to the same shelter, at
# varying degrees of progress so the Logistics Tracker's card states are all
# represented. Buses only, deliberately (CLAUDE.md: pre-disaster predictive
# relocation, not mid-flood rescue — the road network is still intact, so
# there's no boat/amphibious scenario to seed). Covers every seeded
# household exactly once, spread across all 5 seeded buses.
VEHICLE_PLAN: list[tuple[str, str, str, list[str]]] = [
    ("BUS-01", "SH-01", "in_transit", ["HH-112", "HH-104", "HH-107"]),
    ("BUS-02", "SH-02", "assigned", ["HH-118", "HH-203"]),
    ("BUS-03", "SH-01", "in_transit", ["HH-305", "HH-402"]),
    ("BUS-04", "SH-03", "assigned", ["HH-309"]),
    ("BUS-05", "SH-03", "arrived", ["HH-219", "HH-211", "HH-408"]),
]

# zone display_code, household display_code, target review_status — a
# re-verification submission against an already-seeded household, half
# still waiting on SDMA review and half already approved.
SURVEY_PLAN: list[tuple[str, str, str]] = [
    ("ZN-01", "HH-112", "unreviewed"),
    ("ZN-01", "HH-104", "approved"),
    ("ZN-02", "HH-203", "unreviewed"),
    ("ZN-02", "HH-211", "approved"),
    ("ZN-03", "HH-305", "unreviewed"),
    ("ZN-03", "HH-309", "approved"),
    ("ZN-04", "HH-402", "unreviewed"),
    ("ZN-04", "HH-408", "approved"),
]

# code -> current_occupancy, straight from app.seed's own SHELTERS table —
# the one baseline that table's arrival side-effects mutate, so a reset has
# to know what to put it back to rather than just deleting rows.
_BASELINE_SHELTER_OCCUPANCY = {code: occupancy for code, _name, _cap, occupancy, *_rest in SEED_SHELTERS}

# code -> risk_score_72h, straight from app.seed's own ZONES table — the
# baseline a generated forecast's zones.risk_score_72h write (services/
# forecasts.py) needs to be put back to on reset. ZONES' tuple shape is
# (code, name, block, hazards, population, susceptibility, gsi_class,
# gsi_score, risk_72h, confidence, days_since_verified).
_BASELINE_RISK_72H = {code: risk_72h for code, *_mid, risk_72h, _confidence, _days_ago in SEED_ZONES}


def _by_display_code(db: Session, model, code: str):
    return db.scalar(select(model).where(model.display_code == code))


def _clear_relocation_state(db: Session) -> None:
    """Tears down every row the relocation lifecycle created or mutated,
    without touching audit_log (DB-enforced, see module note) or anything
    app.seed itself owns. incident_outcomes/handoff_logs rows that reference
    a relocation_record are deleted first — both have a plain FK to
    relocation_records with no ON DELETE clause, so deleting the record
    first would fail with a FK violation."""
    db.execute(text("delete from incident_outcomes where relocation_record_id in (select record_id from relocation_records)"))
    db.execute(text("delete from handoff_logs where linked_record_id in (select record_id from relocation_records)"))
    db.execute(text("delete from relocation_records"))

    for vehicle in db.scalars(select(Vehicle)).all():
        if vehicle.status != "unavailable":
            vehicle.status = "available"
    for shelter in db.scalars(select(Shelter)).all():
        baseline = _BASELINE_SHELTER_OCCUPANCY.get(shelter.display_code)
        if baseline is not None:
            shelter.current_occupancy = baseline
    for escort in db.scalars(select(Escort)).all():
        escort.status = "available"
    db.commit()


def _clear_forecast_state(db: Session) -> None:
    """Puts the 72-hour forecast screen back to "no forecast cycle run yet"
    for every zone. Needed because "Generate" (services/forecasts.py) jitters
    a real input each cycle, so repeated clicks genuinely diverge from the
    seeded baseline — there's no way back to a fresh-looking state short of
    deleting the generated rows and restoring the one field they mutate.
    incident_outcomes.forecast_id is nulled rather than the outcome row
    deleted: a post-incident feedback entry losing the forecast it was
    logged against is not the same as it never having happened."""
    db.execute(text("update incident_outcomes set forecast_id = null where forecast_id in (select forecast_id from risk_forecasts)"))
    db.execute(text("delete from risk_forecasts"))
    for zone in db.scalars(select(Zone)).all():
        baseline = _BASELINE_RISK_72H.get(zone.display_code)
        if baseline is not None:
            zone.risk_score_72h = baseline
            zone.risk_score_factors = None
    db.commit()


def _clear_change_detection_state(db: Session) -> None:
    """Puts the SAR change-detection screen back to "not run yet" for every
    zone. Needed because a change_detections row is the frontend's only
    signal that a zone's detection has been run this demo cycle (Phase 11's
    interaction-flow fix) — without clearing it here, a zone a judge already
    ran detection on in an earlier cycle would keep showing that stale
    result (and its imagery) right through a reset. incident_outcomes.
    detection_id is nulled rather than the outcome row deleted, same
    reasoning as _clear_forecast_state's forecast_id: a post-incident entry
    losing the detection it was logged against is not the same as it never
    having happened."""
    db.execute(text("update incident_outcomes set detection_id = null where detection_id in (select detection_id from change_detections)"))
    db.execute(text("delete from change_detections"))
    db.commit()


def _reseed_sample_imagery(db: Session) -> None:
    """SAR change detection (Phase 11) needs a curated before/after pair
    per zone to run against at all — found missing live after a reset,
    not because reset ever deleted it (it doesn't touch sample_imagery or
    change_detections), but because no zone other than ZN-01 ever had one
    generated in the first place (app/seed.py only calls
    ensure_sample_imagery_for_zone for ZN-01, once, at initial setup).
    Idempotent (ensure_sample_imagery_for_zone no-ops if a zone's pair
    already exists), so calling it for every zone on every reset is cheap
    and makes "Run detection" work immediately after a reset for any
    zone, not just whichever one happened to get seeded first."""
    for zone in db.scalars(select(Zone)).all():
        ensure_sample_imagery_for_zone(zone.display_code, db)


def seed_demo_relocations(db: Session, actor_id: uuid.UUID) -> DemoSeedResponse:
    _clear_relocation_state(db)
    _clear_forecast_state(db)
    _clear_change_detection_state(db)
    db.execute(text("delete from surveys"))
    _reseed_sample_imagery(db)
    db.commit()

    relocation_items = _seed_relocations(db, actor_id)
    survey_items = _seed_surveys(db, sdma_user_id=actor_id)
    return DemoSeedResponse(
        created=True,
        items=relocation_items,
        counts_by_status=_counts(relocation_items),
        surveys_created=True,
        surveys=survey_items,
    )


def _seed_relocations(db: Session, actor_id: uuid.UUID):
    created = []
    for vehicle_code, shelter_code, target_status, household_codes in VEHICLE_PLAN:
        vehicle = _by_display_code(db, Vehicle, vehicle_code)
        shelter = _by_display_code(db, Shelter, shelter_code)
        if vehicle is None or shelter is None:
            continue

        group_records = []
        for household_code in household_codes:
            household = _by_display_code(db, Household, household_code)
            if household is None:
                continue
            record = relocations_service.create_relocation(
                db,
                RelocationRecordCreate(household_id=household.household_id, shelter_id=shelter.shelter_id, vehicle_id=vehicle.vehicle_id),
                decided_by=actor_id,
            )
            group_records.append(record)

        if target_status in ("in_transit", "arrived"):
            group_records = [
                relocations_service.update_relocation_status(db, r.record_id, "in_transit", actor_id=actor_id) for r in group_records
            ]
        if target_status == "arrived":
            group_records = [
                relocations_service.update_relocation_status(db, r.record_id, "arrived", actor_id=actor_id) for r in group_records
            ]
        created.extend(group_records)

    return created


def _seed_surveys(db: Session, sdma_user_id: uuid.UUID):
    field_officer = db.scalar(select(User).where(User.role == "field_officer").limit(1))
    if field_officer is None:
        return []

    now = datetime.now(timezone.utc)
    created = []
    for index, (zone_code, household_code, target_status) in enumerate(SURVEY_PLAN):
        zone = _by_display_code(db, Zone, zone_code)
        household = _by_display_code(db, Household, household_code)
        if zone is None or household is None:
            continue

        submitted_at = now - timedelta(hours=len(SURVEY_PLAN) - index)
        survey = Survey(
            survey_id=uuid.uuid4(),
            display_code=next_display_code(db, "SV"),
            zone_id=zone.zone_id,
            household_id=household.household_id,
            officer_id=field_officer.user_id,
            submitted_at=submitted_at,
            synced_at=submitted_at,
            payload={
                "population_count": household.population_count,
                "children_count": household.children_count,
                "elderly_count": household.elderly_count,
                "assistance_needs_count": household.assistance_needs_count,
                "structural_condition": household.structural_condition,
            },
            photo_url="sample-photo.jpg",
            review_status="unreviewed" if target_status == "unreviewed" else "approved",
        )
        if target_status == "approved":
            survey.reviewed_by = sdma_user_id
            survey.reviewed_at = submitted_at + timedelta(minutes=30)
        db.add(survey)
        db.flush()  # surfaces any constraint violation per-row rather than batched at commit
        created.append(survey)

    db.commit()
    return created


def _counts(items) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts
