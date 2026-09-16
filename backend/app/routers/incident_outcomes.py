import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, get_scoped_db, require_role
from ..models import User
from ..schemas.incident_outcome import IncidentOutcomeCreate, IncidentOutcomeListResponse, IncidentOutcomeOut
from ..services import incident_outcomes as incident_outcomes_service

router = APIRouter(prefix="/zones", tags=["incident-outcomes"])


@router.post("/{zone_id}/incident-outcomes", response_model=IncidentOutcomeOut, status_code=status.HTTP_201_CREATED)
def create_incident_outcome(
    zone_id: uuid.UUID,
    payload: IncidentOutcomeCreate,
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_role("sdma_official")),
):
    """Phase 13 (PRD §7.12 / TRD §8.4): records the ground-truth outcome of
    an actual incident against a zone — shelter adequacy and route
    reliability are the two questions an authority answers directly, per
    Backend Schema §5.16. Gated to sdma_official, the same role TRD §10
    names as the one that "confirms relocation decisions" — recording
    ground truth is the same class of authority action, not a
    field-officer or read-only control-room one."""
    outcome = incident_outcomes_service.create_outcome(db, zone_id, payload, recorded_by=current_user.user_id)
    if outcome is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return outcome


@router.get("/{zone_id}/incident-outcomes", response_model=IncidentOutcomeListResponse)
def list_incident_outcomes(zone_id: uuid.UUID, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_scoped_db)):
    """RLS on zones scopes this the same way forecasts/change-detections
    are scoped — a field_officer only sees outcomes for their assigned
    zones."""
    outcomes = incident_outcomes_service.list_zone_outcomes(db, zone_id, limit)
    if outcomes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return IncidentOutcomeListResponse(items=outcomes, count=len(outcomes))
