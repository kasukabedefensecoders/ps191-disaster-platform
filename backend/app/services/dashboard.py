from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..schemas.dashboard import DashboardSummary
from ..schemas.handoff import HandoffLogListResponse
from ..schemas.relocation import RelocationRecordListResponse
from ..schemas.route import RouteListResponse
from ..schemas.shelter import ShelterListResponse
from ..schemas.zone import ZoneListResponse
from . import handoffs as handoffs_service
from . import households as households_service
from . import relocations as relocations_service
from . import routes as routes_service
from . import shelters as shelters_service
from . import zones as zones_service

TOP_HOUSEHOLDS_LIMIT = 10
PAGE_LIMIT = 200  # dashboard summary composes whole pages, not paginated sub-lists


def build_dashboard_summary(db: Session, since: datetime | None) -> DashboardSummary:
    zone_items, zone_total = zones_service.list_zones(db, since=since, limit=PAGE_LIMIT, offset=0)
    shelter_items, shelter_total = shelters_service.list_shelters(db, since=since, limit=PAGE_LIMIT, offset=0)
    route_items, route_total = routes_service.list_routes(db, limit=PAGE_LIMIT, offset=0)
    relocation_items, relocation_total = relocations_service.list_relocations(db, limit=PAGE_LIMIT, offset=0)
    handoff_items, handoff_total = handoffs_service.list_handoffs(db, since=since, limit=PAGE_LIMIT, offset=0)

    # Top priority households: computed fresh across every zone this caller
    # can see (RLS-scoped, same as GET /zones), not filtered by `since` —
    # see DashboardSummary's docstring for why.
    all_visible_zones, _ = zones_service.list_zones(db, since=None, limit=PAGE_LIMIT, offset=0)
    ranked_households = []
    for zone in all_visible_zones:
        result = households_service.list_zone_households(db, zone.zone_id, limit=PAGE_LIMIT, offset=0)
        if result is not None:
            items, _ = result
            ranked_households.extend(items)
    ranked_households.sort(key=lambda h: h.priority_score, reverse=True)

    return DashboardSummary(
        since=since,
        generated_at=datetime.now(timezone.utc),
        zones=ZoneListResponse(items=zone_items, count=zone_total, limit=PAGE_LIMIT, offset=0, next_offset=None),
        shelters=ShelterListResponse(items=shelter_items, count=shelter_total, limit=PAGE_LIMIT, offset=0, next_offset=None),
        routes=RouteListResponse(items=route_items, count=route_total, limit=PAGE_LIMIT, offset=0),
        relocations=RelocationRecordListResponse(
            items=relocation_items, count=relocation_total, limit=PAGE_LIMIT, offset=0, next_offset=None
        ),
        handoffs=HandoffLogListResponse(items=handoff_items, count=handoff_total, limit=PAGE_LIMIT, offset=0, next_offset=None),
        top_priority_households=ranked_households[:TOP_HOUSEHOLDS_LIMIT],
    )
