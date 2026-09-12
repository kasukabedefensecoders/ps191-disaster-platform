import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, get_scoped_db, require_role
from ..models import User
from ..schemas.route import BlockedSegmentCreate, RouteCreate, RouteListResponse, RouteOut
from ..services import routes as routes_service

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=RouteListResponse)
def list_routes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_scoped_db),
):
    items, total = routes_service.list_routes(db, limit=limit, offset=offset)
    return RouteListResponse(items=items, count=total, limit=limit, offset=offset)


@router.get("/{route_id}", response_model=RouteOut)
def get_route(route_id: uuid.UUID, db: Session = Depends(get_scoped_db)):
    route = routes_service.get_route(db, route_id)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="route not found")
    return route


@router.post("", response_model=RouteOut, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: RouteCreate,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    return routes_service.create_route(db, payload)


@router.post("/{route_id}/blocked-segments", response_model=RouteOut)
def report_blocked_segment(
    route_id: uuid.UUID,
    payload: BlockedSegmentCreate,
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
):
    """Any authenticated role can report a blockage — TRD §7.7: "blocked-road
    status can be informed by field-report [or] satellite/SAR-based change
    detection" (Phase 11 uses this same endpoint with source='change_detection').
    Not gated to sdma_official like route creation: a field officer spotting
    a landslide-blocked road is exactly who should be able to flag it."""
    route = routes_service.add_blocked_segment(db, route_id, payload, reported_by=str(current_user.user_id))
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="route not found")
    return route


@router.delete("/{route_id}/blocked-segments", response_model=RouteOut)
def clear_blocked_segments(
    route_id: uuid.UUID,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    """Clearing a blockage (road reopened) is an authority confirmation,
    gated the same as other corrections."""
    route = routes_service.clear_blocked_segments(db, route_id)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="route not found")
    return route
