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
