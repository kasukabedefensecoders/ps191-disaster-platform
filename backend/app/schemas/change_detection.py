import uuid
from datetime import datetime

from pydantic import BaseModel


class ChangeDetectionOut(BaseModel):
    detection_id: uuid.UUID
    zone_id: uuid.UUID
    before_image_ref: str
    after_image_ref: str
    affected_area_geom: dict | None
    confidence: float | None
    detected_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ChangeDetectionListResponse(BaseModel):
    items: list[ChangeDetectionOut]
    count: int
