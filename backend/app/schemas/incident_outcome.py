import uuid
from datetime import datetime

from pydantic import BaseModel


class IncidentOutcomeOut(BaseModel):
    outcome_id: uuid.UUID
    zone_id: uuid.UUID
    relocation_record_id: uuid.UUID | None
    forecast_id: uuid.UUID | None
    detection_id: uuid.UUID | None
    occurred_at: datetime
    shelter_adequate: bool | None
    route_held_up: bool | None
    actual_impact: dict | None
    notes: str | None
    recorded_by: uuid.UUID
    recorded_at: datetime
    created_at: datetime
    # Denormalized at read time from the linked forecast (never stored on
    # the row itself) so the screen can show predicted-vs-actual without a
    # second round trip — the whole point of PRD §7.12's feedback loop.
    predicted_score: float | None
    predicted_horizon_hours: int | None


class IncidentOutcomeListResponse(BaseModel):
    items: list[IncidentOutcomeOut]
    count: int


class IncidentOutcomeCreate(BaseModel):
    occurred_at: datetime
    relocation_record_id: uuid.UUID | None = None
    forecast_id: uuid.UUID | None = None
    detection_id: uuid.UUID | None = None
    shelter_adequate: bool | None = None
    route_held_up: bool | None = None
    actual_impact: dict | None = None
    notes: str | None = None
