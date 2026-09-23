import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_shelter, get_scoped_db, require_role
from ..db import get_db
from ..models import Shelter
from ..schemas.shelter import ShelterCreate, ShelterListResponse, ShelterOut, ShelterUpdate
from ..services import shelters as shelters_service
from ..services.shelters import ShelterCapacityError

router = APIRouter(prefix="/shelters", tags=["shelters"])

# Shelter management is sdma_official (registration + oversight) and the
# shelter officer dashboard (occupancy/facilities/needs/status for their own
# shelter, via /shelters/me below) only — field_officer previously had a
# narrow occupancy/needs edit here too, but that's retired now that the
# shelter officer dashboard exists to be the one place ground-level shelter
# data gets entered; a field officer's own PATCH /shelters/{id} is 403 same
# as control_room's, enforced by require_role below rather than a field
# allowlist.
_SHELTER_OFFICER_EDITABLE_FIELDS = {"current_occupancy", "facilities", "needs", "status"}


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


# Registered ahead of GET/PATCH /{shelter_id} so "me" is matched literally
# rather than falling into the {shelter_id}: uuid.UUID path converter.
@router.get("/me", response_model=ShelterOut)
def get_my_shelter(shelter: Shelter = Depends(get_current_shelter), db: Session = Depends(get_db)):
    return shelters_service.get_shelter(db, shelter.shelter_id)


@router.patch("/me", response_model=ShelterOut)
def update_my_shelter(
    payload: ShelterUpdate,
    shelter: Shelter = Depends(get_current_shelter),
    db: Session = Depends(get_db),
):
    attempted = payload.model_dump(exclude_unset=True).keys()
    disallowed = attempted - _SHELTER_OFFICER_EDITABLE_FIELDS
    if disallowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"shelter officer can only update {sorted(_SHELTER_OFFICER_EDITABLE_FIELDS)}, not {sorted(disallowed)}",
        )
    try:
        return shelters_service.update_shelter(db, shelter.shelter_id, payload)
    except ShelterCapacityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
