import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db, require_role
from ..schemas.forecast import ForecastGenerationResponse, ForecastListResponse
from ..services import forecasts as forecasts_service
from ..services.forecasts import ForecastError

router = APIRouter(prefix="/zones", tags=["forecasts"])


@router.post("/{zone_id}/forecasts/generate", response_model=ForecastGenerationResponse)
def generate_forecasts(
    zone_id: uuid.UUID,
    db: Session = Depends(get_scoped_db),
    _: object = Depends(require_role("sdma_official")),
):
    """Phase 10: one generation cycle, one risk_forecasts row per horizon
    bucket (6, 12, 24, 36, 48, 72h). Manually triggered — there's no
    scheduler/cron infra in this build (TRD's Forecasting Service would run
    this on an ingestion cycle in production), so an sdma_official runs a
    cycle explicitly. Also refreshes zones.risk_score_72h, the denormalized
    cache the map reads (Backend Schema §5.3)."""
    try:
        forecasts = forecasts_service.generate_forecasts_for_zone(db, zone_id)
    except ForecastError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if forecasts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return ForecastGenerationResponse(zone_id=zone_id, generated_at=datetime.now(timezone.utc), forecasts=forecasts)


@router.get("/{zone_id}/forecasts", response_model=ForecastListResponse)
def list_forecasts(zone_id: uuid.UUID, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_scoped_db)):
    """RLS on zones (Backend Schema §7) scopes this the same way GET
    /zones/{id} does — a field_officer only sees forecast history for
    their assigned zones."""
    forecasts = forecasts_service.list_zone_forecasts(db, zone_id, limit)
    if forecasts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="zone not found")
    return ForecastListResponse(items=forecasts, count=len(forecasts))
