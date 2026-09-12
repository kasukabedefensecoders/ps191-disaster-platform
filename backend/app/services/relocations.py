import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Escort, Household, RelocationRecord, Shelter, Vehicle, Zone
from ..scoring import match_factors, match_score, prio_factors, prio_score, prio_tier
from ..schemas.relocation import RelocationRecordCreate, RelocationRecordOut
from .audit import write_audit_log
from .display_codes import next_display_code
from .scoring_adapters import household_scoring_dict, zone_scoring_dict
from .shelter_matching import ASSUMED_AVG_SPEED_KMH

FORWARD_TRANSITIONS = {
    "assigned": "in_transit",
    "in_transit": "arrived",
}


class RelocationError(ValueError):
    """A 4xx-worthy problem the router translates to a clean response,
    distinct from a 404 (missing/invisible resource)."""


def _to_out(record: RelocationRecord) -> RelocationRecordOut:
    return RelocationRecordOut.model_validate(record)


def create_relocation(db: Session, payload: RelocationRecordCreate, decided_by: uuid.UUID) -> RelocationRecordOut:
    """The one place a priority_tier gets persisted (Backend Schema §5.4:
    households.priority_tier is live and keeps changing; this is a frozen
    snapshot of what was known *at the moment this decision was made*) —
    and per CLAUDE.md rule 2, the one write this system makes that must
    carry an audit_log row alongside it, in the same transaction.
    """
    household = db.get(Household, payload.household_id)
    if household is None:
        raise LookupError("household")
    zone = db.get(Zone, household.zone_id)

    shelter = db.get(Shelter, payload.shelter_id)
    if shelter is None:
        raise LookupError("shelter")

    vehicle = None
    if payload.vehicle_id is not None:
        vehicle = db.get(Vehicle, payload.vehicle_id)
        if vehicle is None:
            raise LookupError("vehicle")
        if vehicle.status != "available":
            raise RelocationError(f"vehicle is not available (status: {vehicle.status})")

    escort = None
    if payload.escort_id is not None:
        escort = db.get(Escort, payload.escort_id)
        if escort is None:
            raise LookupError("escort")
        if escort.status != "available":
            raise RelocationError(f"escort is not available (status: {escort.status})")

    household_scoring = household_scoring_dict(household)
    zone_scoring = zone_scoring_dict(zone)
    p_factors = prio_factors(household_scoring, zone_scoring)
    p_score = prio_score(household_scoring, zone_scoring)
    tier = prio_tier(p_score)

    effective_need = payload.need if payload.need is not None else household.population_count
    distance_km = float(db.scalar(select(func.ST_DistanceSphere(household.geom, shelter.geom) / 1000.0)))
    duration_minutes = round(distance_km / ASSUMED_AVG_SPEED_KMH * 60, 1)
    route_access = "clear"
    shelter_scoring = {
        "max_capacity": shelter.max_capacity,
        "current_occupancy": shelter.current_occupancy,
        "facilities": shelter.facilities or {},
    }
    a_factors = match_factors(shelter_scoring, effective_need, distance_km, duration_minutes, route_access)
    a_score = match_score(shelter_scoring, effective_need, distance_km, duration_minutes, route_access)

    record = RelocationRecord(
        record_id=uuid.uuid4(),
        display_code=next_display_code(db, "MV", RelocationRecord.display_code),
        household_id=household.household_id,
        shelter_id=shelter.shelter_id,
        vehicle_id=vehicle.vehicle_id if vehicle else None,
        escort_id=escort.escort_id if escort else None,
        priority_tier=tier,
        priority_factors=p_factors,
        allocation_factors=a_factors,
        status="assigned",
        decided_by=decided_by,
    )
    db.add(record)

    if vehicle is not None:
        vehicle.status = "assigned"
    if escort is not None:
        escort.status = "assigned"

    db.flush()  # populates record.record_id (server_default) for the audit row below, without ending the transaction

    write_audit_log(
        db,
        actor_id=decided_by,
        action_type="relocation_decided",
        entity_type="relocation_records",
        entity_id=record.record_id,
        factors_snapshot={
            "priority_tier": tier,
            "priority_score": p_score,
            "priority_factors": p_factors,
            "allocation_score": a_score,
            "allocation_factors": a_factors,
            "shelter_id": str(shelter.shelter_id),
            "vehicle_id": str(vehicle.vehicle_id) if vehicle else None,
            "escort_id": str(escort.escort_id) if escort else None,
        },
    )

    db.commit()
    db.refresh(record)
    return _to_out(record)


def update_relocation_status(
    db: Session, record_id: uuid.UUID, new_status: str, actor_id: uuid.UUID
) -> RelocationRecordOut | None:
    """Returns None if the record doesn't exist. Raises RelocationError for
    an invalid transition (skipping a step, going backward, or an unknown
    status) — the state machine is forward-only, matching the DB's own
    chk_status_timestamps constraint (Backend Schema §5.10)."""
    record = db.get(RelocationRecord, record_id)
    if record is None:
        return None

    expected_next = FORWARD_TRANSITIONS.get(record.status)
    if new_status != expected_next:
        raise RelocationError(
            f"cannot move status from '{record.status}' to '{new_status}' "
            f"(only '{expected_next}' is valid next, if any)"
        )

    now = datetime.now(timezone.utc)
    previous_status = record.status
    record.status = new_status
    if new_status == "in_transit":
        record.in_transit_at = now
        if record.vehicle_id is not None:
            db.get(Vehicle, record.vehicle_id).status = "in_transit"
    elif new_status == "arrived":
        record.arrived_at = now
        if record.vehicle_id is not None:
            db.get(Vehicle, record.vehicle_id).status = "available"
        if record.escort_id is not None:
            db.get(Escort, record.escort_id).status = "available"

    write_audit_log(
        db,
        actor_id=actor_id,
        action_type="relocation_status_changed",
        entity_type="relocation_records",
        entity_id=record.record_id,
        factors_snapshot={"from": previous_status, "to": new_status},
    )

    db.commit()
    db.refresh(record)
    return _to_out(record)


def list_relocations(db: Session, limit: int, offset: int) -> tuple[list[RelocationRecordOut], int]:
    total = db.scalar(select(func.count()).select_from(RelocationRecord)) or 0
    rows = db.scalars(
        select(RelocationRecord).order_by(RelocationRecord.assigned_at.desc()).limit(limit).offset(offset)
    ).all()
    return [_to_out(r) for r in rows], total


def get_relocation(db: Session, record_id: uuid.UUID) -> RelocationRecordOut | None:
    record = db.get(RelocationRecord, record_id)
    return _to_out(record) if record else None
