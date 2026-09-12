import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import VEHICLE_STATUS


class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    district_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("districts.district_id"), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(Text, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(VEHICLE_STATUS, nullable=False, server_default="available")
    current_location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
