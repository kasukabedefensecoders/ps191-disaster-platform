import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db, require_role
from ..schemas.shelter import ShelterCreate, ShelterListResponse, ShelterOut, ShelterUpdate
from ..services import shelters as shelters_service
from ..services.shelters import ShelterCapacityError

router = APIRouter(prefix="/shelters", tags=["shelters"])


@router.get("", response_model=ShelterListResponse)
def list_shelters(
    since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_scoped_db),
):
    """Paginated, since-aware like GET /zones (rule 8). No RLS on shelters
    (Backend Schema §7) — every authenticated role sees the same list."""
    items, total = shelters_service.list_shelters(db, since=since, limit=limit, offset=offset)
    next_offset = offset + limit if offset + limit < total else None
    return ShelterListResponse(items=items, count=total, limit=limit, offset=offset, next_offset=next_offset)


@router.get("/{shelter_id}", response_model=ShelterOut)
def get_shelter(shelter_id: uuid.UUID, db: Session = Depends(get_scoped_db)):
    shelter = shelters_service.get_shelter(db, shelter_id)
    if shelter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="shelter not found")
    return shelter


@router.post("", response_model=ShelterOut, status_code=status.HTTP_201_CREATED)
def create_shelter(
    payload: ShelterCreate,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    try:
        return shelters_service.create_shelter(db, payload)
    except ShelterCapacityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{shelter_id}", response_model=ShelterOut)
def update_shelter(
    shelter_id: uuid.UUID,
    payload: ShelterUpdate,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    try:
        shelter = shelters_service.update_shelter(db, shelter_id, payload)
    except ShelterCapacityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if shelter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="shelter not found")
    return shelter
