import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, get_scoped_db, require_role
from ..models import User
from ..schemas.relocation import (
    RelocationRecordCreate,
    RelocationRecordListResponse,
    RelocationRecordOut,
    RelocationStatusUpdate,
)
from ..services import relocations as relocations_service
from ..services.relocations import RelocationError

router = APIRouter(prefix="/relocations", tags=["relocations"])


@router.get("", response_model=RelocationRecordListResponse)
def list_relocations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_scoped_db),
):
    items, total = relocations_service.list_relocations(db, limit=limit, offset=offset)
    next_offset = offset + limit if offset + limit < total else None
    return RelocationRecordListResponse(items=items, count=total, limit=limit, offset=offset, next_offset=next_offset)


@router.get("/{record_id}", response_model=RelocationRecordOut)
def get_relocation(record_id: uuid.UUID, db: Session = Depends(get_scoped_db)):
    record = relocations_service.get_relocation(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="relocation record not found")
    return record


@router.post("", response_model=RelocationRecordOut, status_code=status.HTTP_201_CREATED)
def create_relocation(
    payload: RelocationRecordCreate,
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_role("sdma_official")),
):
    """Per TRD §10, sdma_official is the role that "confirms relocation
    decisions" — gated the same way zone/shelter writes are. Computes and
    freezes priority_tier/priority_factors and allocation_factors at the
    moment of decision (Backend Schema §5.4/§5.10), and writes the matching
    audit_log row in the same transaction (rule 2)."""
    try:
        return relocations_service.create_relocation(db, payload, decided_by=current_user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{exc} not found") from exc
    except RelocationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{record_id}/status", response_model=RelocationRecordOut)
def update_relocation_status(
    record_id: uuid.UUID,
    payload: RelocationStatusUpdate,
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_role("sdma_official")),
):
    """assigned -> in_transit -> arrived, forward-only (Backend Schema
    §5.10's chk_status_timestamps). Frees the assigned vehicle/escort back
    to 'available' on arrival."""
    try:
        record = relocations_service.update_relocation_status(
            db, record_id, payload.status, actor_id=current_user.user_id
        )
    except RelocationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="relocation record not found")
    return record
