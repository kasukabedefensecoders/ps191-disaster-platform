import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import HAZARD_TYPE, DATA_CONFIDENCE


class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    display_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    district_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("districts.district_id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    geom = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    hazard_types: Mapped[list] = mapped_column(ARRAY(HAZARD_TYPE), nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    incident_history: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    data_confidence: Mapped[str] = mapped_column(DATA_CONFIDENCE, nullable=False, server_default="baseline")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    susceptibility_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    susceptibility_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    gsi_classification: Mapped[str | None] = mapped_column(Text, nullable=True)
    gsi_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    risk_score_72h: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    risk_score_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    risk_score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
