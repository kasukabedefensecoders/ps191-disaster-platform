import uuid
from datetime import datetime

from pydantic import BaseModel


class RelocationRecordOut(BaseModel):
    record_id: uuid.UUID
    display_code: str | None
    household_id: uuid.UUID
    shelter_id: uuid.UUID
    route_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    escort_id: uuid.UUID | None
    priority_tier: str
    priority_factors: list[dict] | None
    allocation_factors: list[dict] | None
    status: str
    decided_by: uuid.UUID
    assigned_at: datetime
    in_transit_at: datetime | None
    arrived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RelocationRecordListResponse(BaseModel):
    items: list[RelocationRecordOut]
    count: int
    limit: int
    offset: int
    next_offset: int | None


class RelocationRecordCreate(BaseModel):
    household_id: uuid.UUID
    shelter_id: uuid.UUID
    vehicle_id: uuid.UUID | None = None
    escort_id: uuid.UUID | None = None
    need: int | None = None  # defaults to the household's population_count


class RelocationStatusUpdate(BaseModel):
    status: str  # "in_transit" or "arrived" — forward-only, see services/relocations.py


class VehicleGroupHouseholdOut(BaseModel):
    """One household's row inside a vehicle's manifest — GET /relocations/
    by-vehicle. Carries display codes and shelter name so the frontend never
    has to cross-reference households/shelters just to render a card (rule
    1: the frontend renders what the API sends)."""

    record_id: uuid.UUID
    display_code: str | None
    household_id: uuid.UUID
    household_display_code: str | None
    shelter_id: uuid.UUID
    shelter_display_code: str | None
    shelter_name: str
    population_count: int
    children_count: int
    elderly_count: int
    assistance_needs_count: int
    priority_tier: str
    status: str
    boarded_at: datetime | None  # = in_transit_at
    arrived_at: datetime | None


class VehicleGroupOut(BaseModel):
    """One vehicle's manifest — several relocation_records consolidated
    onto one bus. vehicle_id is null for the "no vehicle assigned yet"
    bucket, so an unassigned relocation is still visible somewhere rather
    than silently dropped from the tracker."""

    vehicle_id: uuid.UUID | None
    vehicle_display_code: str | None
    vehicle_type: str | None
    route_label: str | None
    capacity: int | None
    current_occupancy: int  # sum of population_count across every household on this manifest
    status: str  # derived from the manifest: in_transit > assigned > arrived, see services/relocations.py
    departed_at: datetime | None  # earliest in_transit_at among the manifest
    estimated_arrival: datetime | None
    households: list[VehicleGroupHouseholdOut]


class RelocationsByVehicleResponse(BaseModel):
    items: list[VehicleGroupOut]
    note: str
