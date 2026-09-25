import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..cv.change_detection import generate_sample_pair, run_change_detection
from ..db import SessionLocal
from ..models import ChangeDetection, Household, SampleImagery, Survey, Zone
from ..schemas.change_detection import ChangeDetectionOut


class ChangeDetectionError(ValueError):
    pass


def _image_keys(zone_display_code: str) -> tuple[str, str]:
    return f"zones/{zone_display_code}/before.png", f"zones/{zone_display_code}/after.png"


def _sample_image_exists(db: Session, zone_display_code: str, kind: str) -> bool:
    return db.get(SampleImagery, (zone_display_code, kind)) is not None


def ensure_sample_imagery_for_zone(zone_display_code: str, db: Session | None = None) -> None:
    """Stores the one curated before/after pair (rule 6: synthetic, not a
    real satellite pass — see app/cv/change_detection.py) directly in
    Postgres (migration 0010) if it isn't already there. Idempotent, safe
    to call on every seed run and on every "Reset demo data" click — takes
    an optional `db` so it can join the caller's own transaction (the reset
    flow) instead of always opening a fresh session (the one-time seed.py
    call, which has none to share)."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        if _sample_image_exists(db, zone_display_code, "before") and _sample_image_exists(db, zone_display_code, "after"):
            return
        before_bytes, after_bytes = generate_sample_pair()
        for kind, data in (("before", before_bytes), ("after", after_bytes)):
            db.merge(SampleImagery(zone_display_code=zone_display_code, kind=kind, content_type="image/png", data=data))
        if owns_session:
            db.commit()
        else:
            db.flush()
    finally:
        if owns_session:
            db.close()


def _to_out(detection: ChangeDetection, geom_geojson: str | None) -> ChangeDetectionOut:
    return ChangeDetectionOut(
        detection_id=detection.detection_id,
        zone_id=detection.zone_id,
        before_image_ref=detection.before_image_ref,
        after_image_ref=detection.after_image_ref,
        affected_area_geom=json.loads(geom_geojson) if geom_geojson else None,
        confidence=float(detection.confidence) if detection.confidence is not None else None,
        cross_referenced_household_ids=list(detection.cross_referenced_household_ids or []),
        cross_referenced_survey_ids=list(detection.cross_referenced_survey_ids or []),
        detected_at=detection.detected_at,
        created_at=detection.created_at,
    )


def _cross_reference(db: Session, zone_id: uuid.UUID, affected_geom) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    """PRD §7.11 / TRD §8.3: the affected-area polygon is cross-referenced
    against households/surveys so the platform reports not just *where*
    impact is but *who* is affected. Scoped to the zone being detected on —
    the same zone RLS already narrows every other read to."""
    household_ids = db.scalars(
        select(Household.household_id).where(
            Household.zone_id == zone_id,
            func.ST_Intersects(Household.geom, affected_geom),
        )
    ).all()
    survey_ids = db.scalars(
        select(Survey.survey_id).where(
            Survey.zone_id == zone_id,
            Survey.geotag.is_not(None),
            func.ST_Intersects(Survey.geotag, affected_geom),
        )
    ).all()
    return list(household_ids), list(survey_ids)


def run_detection_for_zone(db: Session, zone_id: uuid.UUID) -> ChangeDetectionOut | None:
    """Returns None if the zone isn't visible (RLS-hidden or doesn't
    exist). Raises ChangeDetectionError if no curated imagery exists yet
    for this zone — "Reset demo data" (services/demo_seed.py) always calls
    ensure_sample_imagery_for_zone for every seeded zone first, so this
    only fires for a zone created outside that flow."""
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None

    before_row = db.get(SampleImagery, (zone.display_code, "before"))
    after_row = db.get(SampleImagery, (zone.display_code, "after"))
    if before_row is None or after_row is None:
        raise ChangeDetectionError(f"no curated before/after imagery uploaded for zone {zone.display_code!r} yet")

    before_key, after_key = _image_keys(zone.display_code)
    geojson, confidence = run_change_detection(before_row.data, after_row.data)

    detection = ChangeDetection(
        detection_id=uuid.uuid4(),
        zone_id=zone.zone_id,
        before_image_ref=before_key,
        after_image_ref=after_key,
        affected_area_geom=(func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geojson)), 4326) if geojson else None),
        confidence=confidence,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(detection)
    db.flush()

    if geojson:
        affected_geom_expr = (
            select(ChangeDetection.affected_area_geom)
            .where(ChangeDetection.detection_id == detection.detection_id)
            .scalar_subquery()
        )
        household_ids, survey_ids = _cross_reference(db, zone.zone_id, affected_geom_expr)
        detection.cross_referenced_household_ids = household_ids
        detection.cross_referenced_survey_ids = survey_ids

    db.commit()

    row = db.execute(
        select(ChangeDetection, func.ST_AsGeoJSON(ChangeDetection.affected_area_geom)).where(
            ChangeDetection.detection_id == detection.detection_id
        )
    ).first()
    return _to_out(row[0], row[1])


def get_zone_image(db: Session, zone_id: uuid.UUID, which: str) -> bytes | None:
    """Returns None if the zone isn't visible or has no curated imagery.
    Raises ChangeDetectionError for an invalid `which`. Used to actually
    serve the before/after pair to the frontend."""
    if which not in ("before", "after"):
        raise ChangeDetectionError("which must be 'before' or 'after'")
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None
    row = db.get(SampleImagery, (zone.display_code, which))
    return row.data if row is not None else None


def list_zone_detections(db: Session, zone_id: uuid.UUID, limit: int) -> list[ChangeDetectionOut] | None:
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None
    rows = db.execute(
        select(ChangeDetection, func.ST_AsGeoJSON(ChangeDetection.affected_area_geom))
        .where(ChangeDetection.zone_id == zone_id)
        .order_by(ChangeDetection.detected_at.desc())
        .limit(limit)
    ).all()
    return [_to_out(detection, geom_geojson) for detection, geom_geojson in rows]
