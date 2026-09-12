import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import STRUCTURAL_CONDITION, PRIORITY_TIER, DATA_CONFIDENCE


class Household(Base):
    __tablename__ = "households"

    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    display_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.zone_id"), nullable=False)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    population_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    children_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    elderly_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    assistance_needs_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    structural_condition: Mapped[str] = mapped_column(STRUCTURAL_CONDITION, nullable=False, server_default="unknown")
    vulnerability_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    vulnerability_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    priority_tier: Mapped[str | None] = mapped_column(PRIORITY_TIER, nullable=True)
    priority_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    data_confidence: Mapped[str] = mapped_column(DATA_CONFIDENCE, nullable=False, server_default="baseline")
    last_surveyed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
