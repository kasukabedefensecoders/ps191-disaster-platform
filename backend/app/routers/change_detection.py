import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db, require_role
from ..schemas.change_detection import ChangeDetectionListResponse, ChangeDetectionOut
from ..services import change_detection as change_detection_service
from ..services.change_detection import ChangeDetectionError

router = APIRouter(prefix="/zones", tags=["change-detection"])


@router.post("/{zone_id}/change-detections/run", response_model=ChangeDetectionOut)
def run_change_detection(
    zone_id: uuid.UUID,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    """Phase 11: runs the differencing/thresholding pipeline against the
    one curated before/after pair seeded for this zone (see
    app/services/change_detection.py's ensure_sample_imagery_for_zone).
    Gated to sdma_official like the other manually-triggered pipelines
    (Phase 10's forecast generation) in the absence of a real scheduler."""
    try:
        detection = change_detection_service.run_detection_for_zone(db, zone_id)
    except ChangeDetectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return detection


@router.get("/{zone_id}/change-detections/image/{which}")
def get_zone_change_detection_image(zone_id: uuid.UUID, which: Literal["before", "after"], db: Session = Depends(get_scoped_db)):
    """Serves the actual curated before/after PNG bytes (rule 6: the real
    synthetic pair app/cv/change_detection.py generates, not a stock
    photo) — RLS-scoped the same way the rest of change-detection is."""
    try:
        image = change_detection_service.get_zone_image(db, zone_id, which)
    except ChangeDetectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone or imagery not found")
    return Response(content=image, media_type="image/png")


@router.get("/{zone_id}/change-detections", response_model=ChangeDetectionListResponse)
def list_change_detections(zone_id: uuid.UUID, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_scoped_db)):
    """RLS on zones scopes this the same way as forecasts/households."""
    detections = change_detection_service.list_zone_detections(db, zone_id, limit)
    if detections is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return ChangeDetectionListResponse(items=detections, count=len(detections))
