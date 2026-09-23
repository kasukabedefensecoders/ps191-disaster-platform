import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..cv.change_detection import generate_sample_pair, run_change_detection
from ..models import ChangeDetection, Household, Survey, Zone
from ..schemas.change_detection import ChangeDetectionOut
from ..storage import download_bytes, object_exists, upload_bytes


class ChangeDetectionError(ValueError):
    pass


def _image_keys(zone_display_code: str) -> tuple[str, str]:
    return f"zones/{zone_display_code}/before.png", f"zones/{zone_display_code}/after.png"


def ensure_sample_imagery_for_zone(zone_display_code: str) -> None:
    """Uploads the one curated before/after pair (rule 6: synthetic, not a
    real satellite pass — see app/cv/change_detection.py) if it isn't
    already in MinIO. Idempotent, safe to call on every seed run."""
    before_key, after_key = _image_keys(zone_display_code)
    if object_exists(before_key) and object_exists(after_key):
        return
    before_bytes, after_bytes = generate_sample_pair()
    upload_bytes(before_key, before_bytes, "image/png")
    upload_bytes(after_key, after_bytes, "image/png")


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
    exist). Raises ChangeDetectionError if no curated imagery has been
    uploaded for this zone (only ZN-01 has the seeded sample pair)."""
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None

    before_key, after_key = _image_keys(zone.display_code)
    if not (object_exists(before_key) and object_exists(after_key)):
        raise ChangeDetectionError(f"no curated before/after imagery uploaded for zone {zone.display_code!r} yet")

    before_bytes = download_bytes(before_key)
    after_bytes = download_bytes(after_key)
    geojson, confidence = run_change_detection(before_bytes, after_bytes)

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
    serve the before/after pair to the frontend — the change-detection API
    only ever returned MinIO object keys, never the bytes themselves."""
    if which not in ("before", "after"):
        raise ChangeDetectionError("which must be 'before' or 'after'")
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None
    before_key, after_key = _image_keys(zone.display_code)
    key = before_key if which == "before" else after_key
    if not object_exists(key):
        return None
    return download_bytes(key)


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
