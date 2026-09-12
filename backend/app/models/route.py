import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, Integer, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Route(Base):
    __tablename__ = "routes"

    route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    display_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    origin_geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    dest_geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    path = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=False)
    blocked_segments: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    distance_km: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
