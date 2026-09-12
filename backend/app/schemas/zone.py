import uuid
from datetime import datetime

from pydantic import BaseModel


class ZoneOut(BaseModel):
    """Every field CLAUDE.md rule 3 requires (data_confidence, last_verified_at)
    is present unconditionally — this is the one response shape for zones,
    not a slimmer list variant plus a fuller detail variant."""

    zone_id: uuid.UUID
    display_code: str | None
    district_id: uuid.UUID
    name: str
    geom: dict
    hazard_types: list[str]
    population: int
    data_confidence: str
    last_verified_at: datetime | None
    last_verified_by: uuid.UUID | None
    susceptibility_score: float | None
    susceptibility_factors: list[dict] | None
    gsi_classification: str | None
    gsi_score: float | None
    risk_score_72h: float | None
    risk_score_factors: list[dict] | None
    risk_score_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ZoneDetailOut(ZoneOut):
    incident_history: list[dict]
    ml_vs_gsi_divergence_note: str | None


class ZoneListResponse(BaseModel):
    items: list[ZoneOut]
    count: int
    limit: int
    offset: int
    next_offset: int | None


class ZoneCreate(BaseModel):
    display_code: str
    district_id: uuid.UUID
    name: str
    geom: dict
    hazard_types: list[str]
    population: int = 0
    gsi_classification: str | None = None
    gsi_score: float | None = None
    incident_history: list[dict] = []


class ZoneUpdate(BaseModel):
    name: str | None = None
    geom: dict | None = None
    hazard_types: list[str] | None = None
    population: int | None = None
    data_confidence: str | None = None
    susceptibility_score: float | None = None
    susceptibility_factors: list[dict] | None = None
    gsi_classification: str | None = None
    gsi_score: float | None = None
    risk_score_72h: float | None = None
    risk_score_factors: list[dict] | None = None
    incident_history: list[dict] | None = None
