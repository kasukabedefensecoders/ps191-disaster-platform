import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import REVIEW_STATUS


class Survey(Base):
    __tablename__ = "surveys"

    survey_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.zone_id"), nullable=False)
    household_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("households.household_id"), nullable=True)
    officer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    geotag = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    review_status: Mapped[str] = mapped_column(REVIEW_STATUS, nullable=False, server_default="unreviewed")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
