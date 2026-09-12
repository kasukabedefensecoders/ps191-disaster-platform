import uuid
from datetime import datetime

from pydantic import BaseModel


class HouseholdRankedOut(BaseModel):
    """GET /zones/{id}/households row shape. vulnerability_score/factors and
    priority_score/tier/factors are computed live from app.scoring at
    request time (Phase 2), not read from the households table's own
    (currently unpopulated) columns — see services/households.py. Every
    score still returns its factors alongside the number (rule 1), and
    data_confidence/last_surveyed_at travel unconditionally (rule 3)."""

    household_id: uuid.UUID
    display_code: str | None
    zone_id: uuid.UUID
    geom: dict
    population_count: int
    children_count: int
    elderly_count: int
    assistance_needs_count: int
    structural_condition: str
    data_confidence: str
    last_surveyed_at: datetime | None

    vulnerability_score: float
    vulnerability_factors: list[dict]

    priority_score: float
    priority_tier: str
    priority_factors: list[dict]


class HouseholdRankedListResponse(BaseModel):
    items: list[HouseholdRankedOut]
    count: int
    limit: int
    offset: int
    next_offset: int | None
