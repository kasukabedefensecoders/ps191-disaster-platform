import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Household, Survey, Zone
from .display_codes import next_display_code

# Rule 5 (offline-first is a data-model property): survey_id is generated
# client-side, so `insert ... on conflict (survey_id) do update` must never
# create a duplicate row on a retried sync. This function is written so a
# retry with the exact same survey_id and payload — the "dropped connection
# after the server actually succeeded" case BUILD-PLAN's own risk note
# names — reuses whatever household the first attempt created rather than
# creating a second one; see test_survey_sync.py for the retry test this
# was written against, not just the happy path.


class SurveySyncError(ValueError):
    pass


def _sync_one(db: Session, item, officer_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    existing_survey = db.get(Survey, item.survey_id)

    if existing_survey is not None and existing_survey.household_id is not None:
        household_id = existing_survey.household_id
    elif item.household_id is not None:
        household = db.get(Household, item.household_id)
        if household is None:
            raise SurveySyncError("household not found")
        household_id = household.household_id
    else:
        if item.geotag is None:
            raise SurveySyncError("geotag is required to seed a new household")
        zone = db.get(Zone, item.zone_id)
        if zone is None:
            raise SurveySyncError("zone not found")
        household = Household(
            household_id=uuid.uuid4(),
            display_code=next_display_code(db, "HH"),
            zone_id=item.zone_id,
            geom=f"SRID=4326;POINT({item.geotag['coordinates'][0]} {item.geotag['coordinates'][1]})",
            population_count=item.payload.population_count,
            children_count=item.payload.children_count,
            elderly_count=item.payload.elderly_count,
            assistance_needs_count=item.payload.assistance_needs_count,
            structural_condition=item.payload.structural_condition,
        )
        db.add(household)
        db.flush()
        household_id = household.household_id

    household = db.get(Household, household_id)
    household.population_count = item.payload.population_count
    household.children_count = item.payload.children_count
    household.elderly_count = item.payload.elderly_count
    household.assistance_needs_count = item.payload.assistance_needs_count
    household.structural_condition = item.payload.structural_condition
    household.data_confidence = "field_verified"
    household.last_surveyed_at = item.submitted_at

    geotag_expr = None
    if item.geotag is not None:
        lon, lat = item.geotag["coordinates"]
        geotag_expr = f"SRID=4326;POINT({lon} {lat})"

    display_code = existing_survey.display_code if existing_survey is not None else next_display_code(db, "SV")

    stmt = pg_insert(Survey).values(
        survey_id=item.survey_id,
        display_code=display_code,
        zone_id=item.zone_id,
        household_id=household_id,
        officer_id=officer_id,
        submitted_at=item.submitted_at,
        synced_at=datetime.now(timezone.utc),
        payload=item.payload.model_dump(),
        photo_url=item.photo_url,
        geotag=geotag_expr,
    )
    # On a retry, only the fields a resend could plausibly correct are
    # touched — zone_id/household_id/officer_id/submitted_at/review_status
    # stay exactly as first recorded, so a retry can never silently move a
    # survey to a different household or reset a supervisor's review.
    stmt = stmt.on_conflict_do_update(
        index_elements=[Survey.survey_id],
        set_={"payload": stmt.excluded.payload, "synced_at": stmt.excluded.synced_at, "photo_url": stmt.excluded.photo_url, "geotag": stmt.excluded.geotag},
    )
    db.execute(stmt)

    return household_id, display_code


def sync_surveys(db: Session, items, officer_id: uuid.UUID):
    synced = []
    errors = []
    for item in items:
        try:
            with db.begin_nested():
                household_id, survey_display_code = _sync_one(db, item, officer_id)
            synced.append({"survey_id": item.survey_id, "household_id": household_id, "survey_display_code": survey_display_code})
        except SurveySyncError as exc:
            errors.append({"survey_id": item.survey_id, "error": str(exc)})
        except SQLAlchemyError as exc:
            # Broader than SurveySyncError on purpose: an RLS violation (an
            # officer submitting for a zone outside their assignment) or a
            # DB constraint failure surfaces here as a driver-level error,
            # not our own validation type. The SAVEPOINT above already
            # confines the rollback to this one item; the rest of the batch
            # must still get a chance to sync.
            errors.append({"survey_id": item.survey_id, "error": _clean_db_error(exc)})
    db.commit()
    return synced, errors


def _clean_db_error(exc: SQLAlchemyError) -> str:
    message = str(getattr(exc, "orig", exc))
    return message.splitlines()[0][:200]


def list_surveys(db: Session, limit: int, offset: int):
    total = db.scalar(select(func.count()).select_from(Survey)) or 0
    rows = db.scalars(select(Survey).order_by(Survey.submitted_at.desc()).limit(limit).offset(offset)).all()
    return rows, total


def update_review_status(db: Session, survey_id: uuid.UUID, review_status: str, reviewer_id: uuid.UUID) -> Survey | None:
    survey = db.get(Survey, survey_id)
    if survey is None:
        return None
    survey.review_status = review_status
    survey.reviewed_by = reviewer_id
    survey.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(survey)
    return survey
