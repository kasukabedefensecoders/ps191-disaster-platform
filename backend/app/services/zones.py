import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Zone
from ..schemas.zone import ZoneCreate, ZoneDetailOut, ZoneOut, ZoneUpdate

# GSI Bhusanket's own 4-category classification (docs/BACKEND-SCHEMA.md §5.3),
# ordered low -> high for the divergence-direction comparison below.
GSI_CLASS_ORDER = ["Low", "Moderate", "High", "Very High"]


def _susceptibility_to_gsi_bucket(score: float) -> str:
    """Maps the platform's own continuous ML susceptibility_score (0-1) onto
    GSI's 4-category scheme, so the two can be compared on the same axis."""
    if score >= 0.75:
        return "Very High"
    if score >= 0.5:
        return "High"
    if score >= 0.25:
        return "Moderate"
    return "Low"


def ml_vs_gsi_divergence_note(susceptibility_score: float | None, gsi_classification: str | None) -> str | None:
    """Deterministic comparison, not a model — TRD §8.1's genuine ML
    susceptibility refinement is Phase 10, not this. This just formats the
    "agree/disagree, and which direction" note the design system's zone
    detail screen requires (docs/BACKEND-SCHEMA.md §5.3)."""
    if susceptibility_score is None or gsi_classification is None or gsi_classification not in GSI_CLASS_ORDER:
        return None

    ml_bucket = _susceptibility_to_gsi_bucket(susceptibility_score)
    if ml_bucket == gsi_classification:
        return f"ML susceptibility classification agrees with GSI's historical baseline ({gsi_classification})."

    direction = "higher" if GSI_CLASS_ORDER.index(ml_bucket) > GSI_CLASS_ORDER.index(gsi_classification) else "lower"
    return (
        f"ML model rates this zone as {ml_bucket} susceptibility, {direction} than GSI's historical "
        f"baseline of {gsi_classification} — worth review."
    )


def _zone_select():
    return select(Zone, func.ST_AsGeoJSON(Zone.geom).label("geom_geojson"))


def _to_zone_out(zone: Zone, geom_geojson: str, cls=ZoneOut):
    return cls(
        zone_id=zone.zone_id,
        display_code=zone.display_code,
        district_id=zone.district_id,
        name=zone.name,
        geom=json.loads(geom_geojson),
        hazard_types=list(zone.hazard_types),
        population=zone.population,
        data_confidence=zone.data_confidence,
        last_verified_at=zone.last_verified_at,
        last_verified_by=zone.last_verified_by,
        susceptibility_score=zone.susceptibility_score,
        susceptibility_factors=zone.susceptibility_factors,
        gsi_classification=zone.gsi_classification,
        gsi_score=zone.gsi_score,
        risk_score_72h=zone.risk_score_72h,
        risk_score_factors=zone.risk_score_factors,
        risk_score_updated_at=zone.risk_score_updated_at,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
        **(
            {
                "incident_history": zone.incident_history or [],
                "ml_vs_gsi_divergence_note": ml_vs_gsi_divergence_note(
                    float(zone.susceptibility_score) if zone.susceptibility_score is not None else None,
                    zone.gsi_classification,
                ),
            }
            if cls is ZoneDetailOut
            else {}
        ),
    )


def list_zones(db: Session, since: datetime | None, limit: int, offset: int) -> tuple[list[ZoneOut], int]:
    query = _zone_select().order_by(Zone.display_code)
    count_query = select(func.count()).select_from(Zone)
    if since is not None:
        query = query.where(Zone.updated_at > since)
        count_query = count_query.where(Zone.updated_at > since)

    total = db.scalar(count_query) or 0
    rows = db.execute(query.limit(limit).offset(offset)).all()
    return [_to_zone_out(zone, geom_geojson) for zone, geom_geojson in rows], total


def get_zone(db: Session, zone_id) -> ZoneDetailOut | None:
    row = db.execute(_zone_select().where(Zone.zone_id == zone_id)).first()
    if row is None:
        return None
    zone, geom_geojson = row
    return _to_zone_out(zone, geom_geojson, cls=ZoneDetailOut)


def create_zone(db: Session, payload: ZoneCreate) -> ZoneDetailOut:
    zone = Zone(
        display_code=payload.display_code,
        district_id=payload.district_id,
        name=payload.name,
        geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(payload.geom)), 4326),
        hazard_types=payload.hazard_types,
        population=payload.population,
        gsi_classification=payload.gsi_classification,
        gsi_score=payload.gsi_score,
        incident_history=payload.incident_history,
    )
    db.add(zone)
    db.commit()
    # zone.zone_id is already populated post-commit (server_default via
    # RETURNING) — db.refresh(zone) here triggers a SQLAlchemy/GeoAlchemy2
    # identity-lookup bug (binds an empty string instead of the pk for the
    # geometry-bearing table) and is redundant: get_zone() below does its
    # own independent, already-verified SELECT.
    return get_zone(db, zone.zone_id)


def update_zone(db: Session, zone_id, payload: ZoneUpdate) -> ZoneDetailOut | None:
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "geom" in updates:
        zone.geom = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(updates.pop("geom"))), 4326)
    for field, value in updates.items():
        setattr(zone, field, value)

    db.commit()
    return get_zone(db, zone_id)
