import uuid
from datetime import datetime

from sqlalchemy import Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IncidentOutcome(Base):
    __tablename__ = "incident_outcomes"

    outcome_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.zone_id"), nullable=False)
    relocation_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("relocation_records.record_id"), nullable=True)
    forecast_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("risk_forecasts.forecast_id"), nullable=True)
    detection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("change_detections.detection_id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shelter_adequate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    route_held_up: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_impact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
