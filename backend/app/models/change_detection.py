import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ChangeDetection(Base):
    __tablename__ = "change_detections"

    detection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.zone_id"), nullable=False)
    before_image_ref: Mapped[str] = mapped_column(Text, nullable=False)
    after_image_ref: Mapped[str] = mapped_column(Text, nullable=False)
    affected_area_geom = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    cross_referenced_survey_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}")
    cross_referenced_household_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
