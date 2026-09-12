from datetime import datetime

from pydantic import BaseModel

from .household import HouseholdRankedOut
from .relocation import RelocationRecordListResponse
from .route import RouteListResponse
from .shelter import ShelterListResponse
from .zone import ZoneListResponse


class DashboardSummary(BaseModel):
    """rule 8: takes `since` and returns only what changed, for every
    entity type that has one — zones/shelters/relocations are filtered by
    updated_at > since same as their own list endpoints. `routes` and
    `top_priority_households` are always returned in full: routes barely
    change and top_priority_households is a live-computed ranking (Phase 4),
    not a stored, updated_at-bearing row — "since" has no meaning for a
    value that's recomputed fresh every time regardless of what changed."""

    since: datetime | None
    generated_at: datetime
    zones: ZoneListResponse
    shelters: ShelterListResponse
    routes: RouteListResponse
    relocations: RelocationRecordListResponse
    top_priority_households: list[HouseholdRankedOut]
