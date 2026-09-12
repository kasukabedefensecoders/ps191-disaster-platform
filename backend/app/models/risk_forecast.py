import uuid
from datetime import datetime

from sqlalchemy import Text, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RiskForecast(Base):
    __tablename__ = "risk_forecasts"

    forecast_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.zone_id"), nullable=False)
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="72")
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    factors: Mapped[list] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
