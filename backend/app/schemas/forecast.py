import uuid
from datetime import datetime

from pydantic import BaseModel


class RiskForecastOut(BaseModel):
    forecast_id: uuid.UUID
    zone_id: uuid.UUID
    horizon_hours: int
    score: float
    factors: list[dict]
    model_version: str
    generated_at: datetime

    class Config:
        from_attributes = True
        protected_namespaces = ()  # "model_version" collides with pydantic's reserved "model_" prefix otherwise


class ForecastGenerationResponse(BaseModel):
    zone_id: uuid.UUID
    generated_at: datetime
    forecasts: list[RiskForecastOut]


class ForecastListResponse(BaseModel):
    items: list[RiskForecastOut]
    count: int
