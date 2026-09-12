import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db, require_role
from ..schemas.zone import ZoneCreate, ZoneDetailOut, ZoneListResponse, ZoneUpdate
from ..services import zones as zones_service

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=ZoneListResponse)
def list_zones(
    since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_scoped_db),
):
    """Paginated, since-aware per docs/BUILD-PLAN.md Phase 3 and rule 8
    (low-bandwidth by default) — a client re-syncing only asks for what
    changed. RLS on `zones` (Backend Schema §7) scopes the results and the
    total count to what this user's role/zone assignments can see; a
    field_officer's "total" is their assigned-zone total, not the district's."""
    items, total = zones_service.list_zones(db, since=since, limit=limit, offset=offset)
    next_offset = offset + limit if offset + limit < total else None
    return ZoneListResponse(items=items, count=total, limit=limit, offset=offset, next_offset=next_offset)


@router.get("/{zone_id}", response_model=ZoneDetailOut)
def get_zone(zone_id: uuid.UUID, db: Session = Depends(get_scoped_db)):
    zone = zones_service.get_zone(db, zone_id)
    if zone is None:
        # RLS hides out-of-scope zones the same way as nonexistent ones —
        # a field_officer's 404 for an unassigned zone must not distinguish
        # "doesn't exist" from "exists but isn't yours" (Backend Schema §7).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return zone


@router.post("", response_model=ZoneDetailOut, status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreate,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    return zones_service.create_zone(db, payload)


@router.patch("/{zone_id}", response_model=ZoneDetailOut)
def update_zone(
    zone_id: uuid.UUID,
    payload: ZoneUpdate,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    zone = zones_service.update_zone(db, zone_id, payload)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return zone
