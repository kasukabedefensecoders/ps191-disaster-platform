import uuid
from datetime import datetime

from pydantic import BaseModel


class ShelterOut(BaseModel):
    shelter_id: uuid.UUID
    display_code: str | None
    district_id: uuid.UUID
    name: str
    geom: dict
    max_capacity: int
    current_occupancy: int
    facilities: dict
    status: str
    last_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ShelterListResponse(BaseModel):
    items: list[ShelterOut]
    count: int
    limit: int
    offset: int
    next_offset: int | None


class ShelterCreate(BaseModel):
    display_code: str
    district_id: uuid.UUID
    name: str
    geom: dict
    max_capacity: int
    current_occupancy: int = 0
    facilities: dict = {}
    status: str = "active"


class ShelterUpdate(BaseModel):
    name: str | None = None
    geom: dict | None = None
    max_capacity: int | None = None
    current_occupancy: int | None = None
    facilities: dict | None = None
    status: str | None = None


class ShelterMatchOut(ShelterOut):
    distance_km: float
    duration_minutes: float
    route_access: str
    match_score: float
    match_factors: list[dict]


class ShelterMatchListResponse(BaseModel):
    items: list[ShelterMatchOut]
    count: int
    need: int
    note: str
