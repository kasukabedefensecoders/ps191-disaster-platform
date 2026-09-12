import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Shelter
from ..schemas.shelter import ShelterCreate, ShelterOut, ShelterUpdate

# shelters carry no RLS (Backend Schema §7 only covers households/zones/
# surveys) — shelter capacity/location isn't the sensitive data rule 7
# protects, so every authenticated role sees the same shelter list.


class ShelterCapacityError(ValueError):
    """current_occupancy > max_capacity — the DB's own chk_occupancy_within_
    capacity constraint is authoritative (Backend Schema §5.5); this just
    turns that IntegrityError into a clean 400 instead of a raw 500."""


def _commit_or_raise_capacity_error(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "chk_occupancy_within_capacity" in str(exc.orig):
            raise ShelterCapacityError("current_occupancy cannot exceed max_capacity") from exc
        raise


def _shelter_select():
    return select(Shelter, func.ST_AsGeoJSON(Shelter.geom).label("geom_geojson"))


def _to_shelter_out(shelter: Shelter, geom_geojson: str, cls=ShelterOut, **extra):
    return cls(
        shelter_id=shelter.shelter_id,
        display_code=shelter.display_code,
        district_id=shelter.district_id,
        name=shelter.name,
        geom=json.loads(geom_geojson),
        max_capacity=shelter.max_capacity,
        current_occupancy=shelter.current_occupancy,
        facilities=shelter.facilities or {},
        status=shelter.status,
        last_updated_at=shelter.last_updated_at,
        created_at=shelter.created_at,
        updated_at=shelter.updated_at,
        **extra,
    )


def list_shelters(db: Session, since: datetime | None, limit: int, offset: int) -> tuple[list[ShelterOut], int]:
    query = _shelter_select().order_by(Shelter.display_code)
    count_query = select(func.count()).select_from(Shelter)
    if since is not None:
        query = query.where(Shelter.updated_at > since)
        count_query = count_query.where(Shelter.updated_at > since)

    total = db.scalar(count_query) or 0
    rows = db.execute(query.limit(limit).offset(offset)).all()
    return [_to_shelter_out(shelter, geom_geojson) for shelter, geom_geojson in rows], total


def get_shelter(db: Session, shelter_id) -> ShelterOut | None:
    row = db.execute(_shelter_select().where(Shelter.shelter_id == shelter_id)).first()
    if row is None:
        return None
    shelter, geom_geojson = row
    return _to_shelter_out(shelter, geom_geojson)


def create_shelter(db: Session, payload: ShelterCreate) -> ShelterOut:
    shelter = Shelter(
        display_code=payload.display_code,
        district_id=payload.district_id,
        name=payload.name,
        geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(payload.geom)), 4326),
        max_capacity=payload.max_capacity,
        current_occupancy=payload.current_occupancy,
        facilities=payload.facilities,
        status=payload.status,
    )
    db.add(shelter)
    _commit_or_raise_capacity_error(db)
    # See services/zones.py's create_zone comment — no db.refresh() here for
    # the same reason: shelter.shelter_id is already populated post-commit,
    # and get_shelter() below does its own independent, already-verified
    # SELECT rather than relying on refresh's identity-lookup path.
    return get_shelter(db, shelter.shelter_id)


def update_shelter(db: Session, shelter_id, payload: ShelterUpdate) -> ShelterOut | None:
    shelter = db.get(Shelter, shelter_id)
    if shelter is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "geom" in updates:
        shelter.geom = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(updates.pop("geom"))), 4326)
    for field, value in updates.items():
        setattr(shelter, field, value)

    _commit_or_raise_capacity_error(db)
    return get_shelter(db, shelter_id)
