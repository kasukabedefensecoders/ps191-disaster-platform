import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Escort, HandoffLog, Household, RelocationRecord, Shelter, Vehicle, Zone
from ..scoring import match_factors, match_score, prio_factors, prio_score, prio_tier
from ..schemas.relocation import (
    RelocationRecordCreate,
    RelocationRecordOut,
    RelocationsByVehicleResponse,
    VehicleGroupHouseholdOut,
    VehicleGroupOut,
)
from .audit import write_audit_log
from .display_codes import next_display_code
from .scoring_adapters import household_scoring_dict, zone_scoring_dict
from .shelter_matching import ASSUMED_AVG_SPEED_KMH

FORWARD_TRANSITIONS = {
    "assigned": "in_transit",
    "in_transit": "arrived",
}

# Logistics Tracker's bus-card ordering: whatever needs eyes right now
# (moving) first, then what's still waiting to depart, arrived/done last.
_GROUP_STATUS_ORDER = {"in_transit": 0, "assigned": 1, "arrived": 2}

BY_VEHICLE_NOTE = (
    "estimated_arrival is departed_at plus a straight-line distance / "
    f"{ASSUMED_AVG_SPEED_KMH:.0f} km/h planning estimate per household on the manifest (the same proxy "
    "services/shelter_matching.py uses), not a routed ETA — Phase 7 routing isn't built yet."
)

# A vehicle's capacity is shared across every household riding it, not
# reserved for one relocation_record at a time (a bus consolidating several
# households onto one run — Logistics Tracker's bus cards). "Committed"
# population is summed over every non-arrived relocation_record currently
# on that vehicle; a fresh vehicle's committed population is 0.
def _vehicle_committed_population(db: Session, vehicle_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.coalesce(func.sum(Household.population_count), 0))
            .select_from(RelocationRecord)
            .join(Household, Household.household_id == RelocationRecord.household_id)
            .where(RelocationRecord.vehicle_id == vehicle_id, RelocationRecord.status != "arrived")
        )
        or 0
    )


# Change 2's "vehicle_id: auto-assigned (Bus-01, or least-occupied bus)" —
# an sdma_official allocating a household doesn't have to already know the
# vehicle roster. Best-fit-first (smallest *remaining* capacity that still
# covers the need, considering households already committed to that
# vehicle) so a single household doesn't tie up a large bus another
# household needs more; if nothing fits, the vehicle with the most
# remaining capacity is still better than leaving the pickup unassigned.
# 'unavailable' vehicles (out of service) are never candidates.
def _auto_select_vehicle(db: Session, effective_need: int) -> Vehicle | None:
    candidates = db.scalars(select(Vehicle).where(Vehicle.status != "unavailable")).all()
    if not candidates:
        return None
    remaining = {v.vehicle_id: v.capacity - _vehicle_committed_population(db, v.vehicle_id) for v in candidates}
    fitting = [v for v in candidates if remaining[v.vehicle_id] >= effective_need]
    if fitting:
        return min(fitting, key=lambda v: remaining[v.vehicle_id])
    return max(candidates, key=lambda v: remaining[v.vehicle_id])


# Re-derives a vehicle's status from the relocation_records actually riding
# it, rather than a hardcoded assignment — with several households sharing
# one vehicle, the first one arriving must not free the vehicle while
# others are still in transit on it, and the first one departing should
# move the whole vehicle to 'in_transit' even if others on it are still
# 'assigned' (physically it's one bus that has now left).
def _recompute_vehicle_status(db: Session, vehicle_id: uuid.UUID) -> None:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.status == "unavailable":
        return
    active_statuses = set(
        db.scalars(
            select(RelocationRecord.status).where(RelocationRecord.vehicle_id == vehicle_id, RelocationRecord.status != "arrived")
        ).all()
    )
    if not active_statuses:
        vehicle.status = "available"
    elif "in_transit" in active_statuses:
        vehicle.status = "in_transit"
    else:
        vehicle.status = "assigned"


# Change 3's "auto-generate handoff needs if household has vulnerable
# members" — raised the moment a relocation is confirmed delivered, since
# that's when the receiving shelter/agency actually needs to act on them.
# Thresholds mirror the same household fields CLAUDE.md's vulnerability
# scoring already weighs (children/elderly/population), not a new axis.
def _auto_handoffs_on_arrival(db: Session, record: RelocationRecord, household: Household) -> None:
    needs: list[tuple[str, str]] = []
    if household.children_count > 0:
        needs.append(("Child care", "District Child Welfare Committee"))
    if household.elderly_count > 0:
        needs.append(("Elderly medical assistance", "District Health Department"))
    if household.population_count > 8:
        needs.append(("Logistics support — large household", "SDMA Logistics Cell"))

    for need_type, agency in needs:
        db.add(
            HandoffLog(
                display_code=next_display_code(db, "HO"),
                need_type=need_type,
                agency=agency,
                linked_record_id=record.record_id,
                household_id=household.household_id,
                description=f"Auto-flagged on arrival of {record.display_code} ({household.display_code}).",
            )
        )


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

    effective_need = payload.need if payload.need is not None else household.population_count

    vehicle = None
    if payload.vehicle_id is not None:
        vehicle = db.get(Vehicle, payload.vehicle_id)
        if vehicle is None:
            raise LookupError("vehicle")
        if vehicle.status == "unavailable":
            raise RelocationError(f"vehicle is not available (status: {vehicle.status})")
        committed = _vehicle_committed_population(db, vehicle.vehicle_id)
        if committed + effective_need > vehicle.capacity:
            raise RelocationError(
                f"vehicle over capacity: {committed} already committed + {effective_need} needed > {vehicle.capacity} capacity"
            )
    else:
        vehicle = _auto_select_vehicle(db, effective_need)

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
        display_code=next_display_code(db, "MV"),
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
    db.flush()  # populates record.record_id (server_default) for the audit row below, without ending the transaction

    if vehicle is not None:
        _recompute_vehicle_status(db, vehicle.vehicle_id)
    if escort is not None:
        escort.status = "assigned"

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
    # No db.refresh() here — see services/shelters.py's create_shelter for
    # the same reasoning: expire_on_commit=False (app/db.py) means `record`
    # already carries every value RETURNING populated at flush time, so a
    # refresh only adds a second query. That query would run in a new
    # transaction after commit() released this session's connection back to
    # the pool, and could be handed a *different* pooled connection whose
    # app.current_role/current_user_id (session-scoped GUCs, set once per
    # request in get_scoped_db) belong to whatever request last used it —
    # tripping relocation_records' RLS policy with a stale or empty
    # app.current_user_id. Real, reproducible under concurrent requests
    # (a UUID cast failure on an empty current_user_id), not hypothetical.
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
            db.flush()  # so the recompute query below sees this record's new status
            _recompute_vehicle_status(db, record.vehicle_id)
    elif new_status == "arrived":
        record.arrived_at = now
        if record.vehicle_id is not None:
            db.flush()
            _recompute_vehicle_status(db, record.vehicle_id)
        if record.escort_id is not None:
            db.get(Escort, record.escort_id).status = "available"

        household = db.get(Household, record.household_id)
        shelter = db.get(Shelter, record.shelter_id)
        shelter.current_occupancy = min(shelter.current_occupancy + household.population_count, shelter.max_capacity)
        shelter.last_updated_at = now
        _auto_handoffs_on_arrival(db, record, household)

    write_audit_log(
        db,
        actor_id=actor_id,
        action_type="relocation_status_changed",
        entity_type="relocation_records",
        entity_id=record.record_id,
        factors_snapshot={"from": previous_status, "to": new_status},
    )

    db.commit()
    return _to_out(record)


def list_relocations(
    db: Session, limit: int, offset: int, since: datetime | None = None
) -> tuple[list[RelocationRecordOut], int]:
    query = select(RelocationRecord).order_by(RelocationRecord.assigned_at.desc())
    count_query = select(func.count()).select_from(RelocationRecord)
    if since is not None:
        query = query.where(RelocationRecord.updated_at > since)
        count_query = count_query.where(RelocationRecord.updated_at > since)

    total = db.scalar(count_query) or 0
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return [_to_out(r) for r in rows], total


def get_relocation(db: Session, record_id: uuid.UUID) -> RelocationRecordOut | None:
    record = db.get(RelocationRecord, record_id)
    return _to_out(record) if record else None


def group_relocations_by_vehicle(db: Session) -> RelocationsByVehicleResponse:
    """Change 3's bus-consolidation view: several relocation_records sharing
    one vehicle_id, rolled up into one manifest per vehicle. A read-side
    aggregation only — relocation_records itself stays the source of truth,
    this just groups what's already there (rule 1: never invent a number
    the underlying data doesn't support)."""
    rows = db.execute(
        select(
            RelocationRecord,
            Household,
            Shelter,
            Vehicle,
            (func.ST_DistanceSphere(Household.geom, Shelter.geom) / 1000.0).label("distance_km"),
        )
        .join(Household, Household.household_id == RelocationRecord.household_id)
        .join(Shelter, Shelter.shelter_id == RelocationRecord.shelter_id)
        .outerjoin(Vehicle, Vehicle.vehicle_id == RelocationRecord.vehicle_id)
    ).all()

    groups: dict[uuid.UUID | None, dict] = {}
    for record, household, shelter, vehicle, distance_km in rows:
        key = record.vehicle_id
        group = groups.setdefault(
            key,
            {"vehicle": vehicle, "households": [], "in_transit_ats": [], "durations_minutes": []},
        )
        group["households"].append(
            VehicleGroupHouseholdOut(
                record_id=record.record_id,
                display_code=record.display_code,
                household_id=household.household_id,
                household_display_code=household.display_code,
                shelter_id=shelter.shelter_id,
                shelter_display_code=shelter.display_code,
                shelter_name=shelter.name,
                population_count=household.population_count,
                children_count=household.children_count,
                elderly_count=household.elderly_count,
                assistance_needs_count=household.assistance_needs_count,
                priority_tier=record.priority_tier,
                status=record.status,
                boarded_at=record.in_transit_at,
                arrived_at=record.arrived_at,
            )
        )
        if record.in_transit_at is not None:
            group["in_transit_ats"].append(record.in_transit_at)
            group["durations_minutes"].append(round(float(distance_km) / ASSUMED_AVG_SPEED_KMH * 60, 1))

    items: list[VehicleGroupOut] = []
    for key, group in groups.items():
        vehicle: Vehicle | None = group["vehicle"]
        households: list[VehicleGroupHouseholdOut] = group["households"]
        statuses = {h.status for h in households}
        group_status = min(statuses, key=lambda s: _GROUP_STATUS_ORDER.get(s, 99)) if statuses else "assigned"
        departed_at = min(group["in_transit_ats"]) if group["in_transit_ats"] else None
        estimated_arrival = None
        if departed_at is not None and group["durations_minutes"]:
            estimated_arrival = departed_at + timedelta(minutes=max(group["durations_minutes"]))

        items.append(
            VehicleGroupOut(
                vehicle_id=key,
                vehicle_display_code=vehicle.display_code if vehicle else None,
                vehicle_type=vehicle.vehicle_type if vehicle else None,
                route_label=vehicle.route_label if vehicle else None,
                capacity=vehicle.capacity if vehicle else None,
                current_occupancy=sum(h.population_count for h in households),
                status=group_status,
                departed_at=departed_at,
                estimated_arrival=estimated_arrival,
                households=sorted(households, key=lambda h: h.boarded_at or datetime.min.replace(tzinfo=timezone.utc)),
            )
        )

    items.sort(key=lambda g: (_GROUP_STATUS_ORDER.get(g.status, 99), g.vehicle_display_code or ""))
    return RelocationsByVehicleResponse(items=items, note=BY_VEHICLE_NOTE)
