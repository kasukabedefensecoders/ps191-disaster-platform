import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import HAZARD_TYPE


class District(Base):
    __tablename__ = "districts"

    district_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    geom = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True)
    primary_hazards: Mapped[list] = mapped_column(ARRAY(HAZARD_TYPE), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
