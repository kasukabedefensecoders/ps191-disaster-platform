import uuid
from datetime import datetime

from pydantic import BaseModel


class RouteOut(BaseModel):
    route_id: uuid.UUID
    display_code: str | None
    origin_geom: dict
    dest_geom: dict
    path: dict
    blocked_segments: list[dict]
    distance_km: float | None
    estimated_duration_minutes: int | None
    created_at: datetime
    updated_at: datetime


class RouteListResponse(BaseModel):
    items: list[RouteOut]
    count: int
    limit: int
    offset: int


class RouteCreate(BaseModel):
    origin_geom: dict
    dest_geom: dict
    path: dict
    distance_km: float | None = None
    estimated_duration_minutes: int | None = None


class BlockedSegmentCreate(BaseModel):
    """Backend Schema §6.4 shape. `source` is 'field_report' (an officer
    reporting a blockage) or 'change_detection' (Phase 11's CV pipeline)."""

    osm_way_id: str | None = None
    reason: str
    source: str = "field_report"
