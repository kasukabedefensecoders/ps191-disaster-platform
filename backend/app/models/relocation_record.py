import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import PRIORITY_TIER, RELOCATION_STATUS


class RelocationRecord(Base):
    __tablename__ = "relocation_records"
    __table_args__ = (
        CheckConstraint(
            "(status = 'assigned') or "
            "(status = 'in_transit' and in_transit_at is not null) or "
            "(status = 'arrived' and in_transit_at is not null and arrived_at is not null)",
            name="chk_status_timestamps",
        ),
    )

    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    display_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("households.household_id"), nullable=False)
    shelter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shelters.shelter_id"), nullable=False)
    route_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("routes.route_id"), nullable=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.vehicle_id"), nullable=True)
    escort_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("escorts.escort_id"), nullable=True)
    priority_tier: Mapped[str] = mapped_column(PRIORITY_TIER, nullable=False)
    priority_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    allocation_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(RELOCATION_STATUS, nullable=False, server_default="assigned")
    decided_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    in_transit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
