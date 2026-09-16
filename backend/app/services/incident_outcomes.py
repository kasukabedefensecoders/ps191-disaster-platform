import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ChangeDetection, IncidentOutcome, RiskForecast, Zone
from ..schemas.incident_outcome import IncidentOutcomeCreate, IncidentOutcomeOut


def _to_out(outcome: IncidentOutcome, predicted_score: float | None, predicted_horizon_hours: int | None) -> IncidentOutcomeOut:
    return IncidentOutcomeOut(
        outcome_id=outcome.outcome_id,
        zone_id=outcome.zone_id,
        relocation_record_id=outcome.relocation_record_id,
        forecast_id=outcome.forecast_id,
        detection_id=outcome.detection_id,
        occurred_at=outcome.occurred_at,
        shelter_adequate=outcome.shelter_adequate,
        route_held_up=outcome.route_held_up,
        actual_impact=outcome.actual_impact,
        notes=outcome.notes,
        recorded_by=outcome.recorded_by,
        recorded_at=outcome.recorded_at,
        created_at=outcome.created_at,
        predicted_score=predicted_score,
        predicted_horizon_hours=predicted_horizon_hours,
    )


def _nearest_forecast_before(db: Session, zone_id: uuid.UUID, occurred_at: datetime) -> RiskForecast | None:
    """Auto-correlates the outcome with the 72h forecast cycle that was
    live for this zone right before the incident — the "what did the model
    predict just before this happened" comparison TRD §8.4's feedback loop
    needs, without asking the recording officer to hunt down a forecast_id
    by hand."""
    return db.scalars(
        select(RiskForecast)
        .where(RiskForecast.zone_id == zone_id, RiskForecast.generated_at <= occurred_at, RiskForecast.horizon_hours == 72)
        .order_by(RiskForecast.generated_at.desc())
        .limit(1)
    ).first()


def _nearest_detection_before(db: Session, zone_id: uuid.UUID, occurred_at: datetime) -> ChangeDetection | None:
    return db.scalars(
        select(ChangeDetection)
        .where(ChangeDetection.zone_id == zone_id, ChangeDetection.detected_at <= occurred_at)
        .order_by(ChangeDetection.detected_at.desc())
        .limit(1)
    ).first()


def create_outcome(
    db: Session, zone_id: uuid.UUID, payload: IncidentOutcomeCreate, recorded_by: uuid.UUID
) -> IncidentOutcomeOut | None:
    """Returns None if the zone isn't visible (RLS-hidden or doesn't
    exist), the same 404-hides-existence pattern used everywhere else."""
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None

    forecast_id = payload.forecast_id
    if forecast_id is None:
        forecast = _nearest_forecast_before(db, zone_id, payload.occurred_at)
        forecast_id = forecast.forecast_id if forecast else None

    detection_id = payload.detection_id
    if detection_id is None:
        detection = _nearest_detection_before(db, zone_id, payload.occurred_at)
        detection_id = detection.detection_id if detection else None

    outcome = IncidentOutcome(
        outcome_id=uuid.uuid4(),
        zone_id=zone_id,
        relocation_record_id=payload.relocation_record_id,
        forecast_id=forecast_id,
        detection_id=detection_id,
        occurred_at=payload.occurred_at,
        shelter_adequate=payload.shelter_adequate,
        route_held_up=payload.route_held_up,
        actual_impact=payload.actual_impact,
        notes=payload.notes,
        recorded_by=recorded_by,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    predicted_score = None
    predicted_horizon = None
    if outcome.forecast_id is not None:
        forecast = db.get(RiskForecast, outcome.forecast_id)
        if forecast is not None:
            predicted_score = float(forecast.score)
            predicted_horizon = forecast.horizon_hours

    return _to_out(outcome, predicted_score, predicted_horizon)


def list_zone_outcomes(db: Session, zone_id: uuid.UUID, limit: int) -> list[IncidentOutcomeOut] | None:
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None

    rows = db.scalars(
        select(IncidentOutcome)
        .where(IncidentOutcome.zone_id == zone_id)
        .order_by(IncidentOutcome.occurred_at.desc())
        .limit(limit)
    ).all()

    forecast_ids = {r.forecast_id for r in rows if r.forecast_id is not None}
    forecasts_by_id: dict[uuid.UUID, RiskForecast] = {}
    if forecast_ids:
        forecasts = db.scalars(select(RiskForecast).where(RiskForecast.forecast_id.in_(forecast_ids))).all()
        forecasts_by_id = {f.forecast_id: f for f in forecasts}

    out = []
    for row in rows:
        forecast = forecasts_by_id.get(row.forecast_id) if row.forecast_id else None
        out.append(_to_out(row, float(forecast.score) if forecast else None, forecast.horizon_hours if forecast else None))
    return out
