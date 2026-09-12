import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

VALID_STATUSES = ("open", "acknowledged", "in_progress", "resolved")


class HandoffLogOut(BaseModel):
    log_id: uuid.UUID
    display_code: str | None
    need_type: str
    agency: str
    status: str
    linked_record_id: uuid.UUID | None
    zone_id: uuid.UUID | None
    household_id: uuid.UUID | None
    description: str | None
    raised_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HandoffLogListResponse(BaseModel):
    items: list[HandoffLogOut]
    count: int
    limit: int
    offset: int
    next_offset: int | None


class HandoffLogCreate(BaseModel):
    need_type: str
    agency: str
    description: str | None = None
    linked_record_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    household_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _require_context(self):
        # Mirrors chk_handoff_has_context (Backend Schema §5.14) at the API
        # layer so a bad request gets a clean 422 instead of surfacing as a
        # raw DB constraint violation — the DB check stays the real
        # authority either way.
        if not (self.linked_record_id or self.zone_id or self.household_id):
            raise ValueError("at least one of linked_record_id, zone_id, household_id is required")
        return self


class HandoffStatusUpdate(BaseModel):
    status: str

    @model_validator(mode="after")
    def _valid_status(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return self
