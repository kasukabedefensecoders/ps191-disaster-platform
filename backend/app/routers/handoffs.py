import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db, require_role
from ..schemas.handoff import HandoffLogCreate, HandoffLogListResponse, HandoffLogOut, HandoffStatusUpdate
from ..services import handoffs as handoffs_service

router = APIRouter(prefix="/handoffs", tags=["handoffs"])


@router.get("", response_model=HandoffLogListResponse)
def list_handoffs(
    since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_scoped_db),
):
    items, total = handoffs_service.list_handoffs(db, since=since, limit=limit, offset=offset)
    next_offset = offset + limit if offset + limit < total else None
    return HandoffLogListResponse(items=items, count=total, limit=limit, offset=offset, next_offset=next_offset)


@router.get("/{log_id}", response_model=HandoffLogOut)
def get_handoff(log_id: uuid.UUID, db: Session = Depends(get_scoped_db)):
    handoff = handoffs_service.get_handoff(db, log_id)
    if handoff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="handoff not found")
    return handoff


@router.post("", response_model=HandoffLogOut, status_code=status.HTTP_201_CREATED)
def create_handoff(payload: HandoffLogCreate, db: Session = Depends(get_scoped_db)):
    """Any authenticated role can raise a handoff (PRD §7.13 — a field
    officer spotting a medical/rescue need should be able to route it
    directly, not need sdma_official to file it for them), unlike status
    updates below which are an authority confirmation."""
    return handoffs_service.create_handoff(db, payload)


@router.patch("/{log_id}/status", response_model=HandoffLogOut)
def update_handoff_status(
    log_id: uuid.UUID,
    payload: HandoffStatusUpdate,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    handoff = handoffs_service.update_status(db, log_id, payload.status)
    if handoff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="handoff not found")
    return handoff
