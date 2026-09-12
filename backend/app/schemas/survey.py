import uuid
from datetime import datetime

from pydantic import BaseModel


class SurveyPayload(BaseModel):
    """Backend Schema §6.5 shape — mirrors the household vulnerability-
    assessment fields exactly (PRD §7.10) so this can be applied straight
    onto a households row with no translation step."""

    population_count: int
    children_count: int
    elderly_count: int
    assistance_needs_count: int
    structural_condition: str
    notes: str | None = None


class SurveySyncItem(BaseModel):
    """survey_id is client-generated (Backend Schema §5.6 — the field PWA
    assigns it before connectivity exists, not the server), which is what
    makes a retried sync idempotent rather than duplicating."""

    survey_id: uuid.UUID
    zone_id: uuid.UUID
    household_id: uuid.UUID | None = None
    submitted_at: datetime
    payload: SurveyPayload
    photo_url: str | None = None
    geotag: dict | None = None  # GeoJSON Point; required when household_id is None


class SurveySyncRequest(BaseModel):
    surveys: list[SurveySyncItem]


class SurveySyncResult(BaseModel):
    survey_id: uuid.UUID
    survey_display_code: str  # e.g. SV-4471 — not the household's own display_code
    household_id: uuid.UUID


class SurveySyncError(BaseModel):
    survey_id: uuid.UUID
    error: str


class SurveySyncResponse(BaseModel):
    synced: list[SurveySyncResult]
    errors: list[SurveySyncError]


class SurveyOut(BaseModel):
    survey_id: uuid.UUID
    display_code: str | None
    zone_id: uuid.UUID
    household_id: uuid.UUID | None
    officer_id: uuid.UUID
    submitted_at: datetime
    synced_at: datetime | None
    payload: dict
    photo_url: str | None
    review_status: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SurveyListResponse(BaseModel):
    items: list[SurveyOut]
    count: int
    limit: int
    offset: int


class SurveyReviewUpdate(BaseModel):
    review_status: str  # "approved" or "flagged"
