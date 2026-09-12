import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import HANDOFF_STATUS


class HandoffLog(Base):
    __tablename__ = "handoff_logs"
    __table_args__ = (
        CheckConstraint(
            "linked_record_id is not null or zone_id is not null or household_id is not null",
            name="chk_handoff_has_context",
        ),
    )

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    display_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    need_type: Mapped[str] = mapped_column(Text, nullable=False)
    agency: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(HANDOFF_STATUS, nullable=False, server_default="open")
    linked_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("relocation_records.record_id"), nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.zone_id"), nullable=True)
    household_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("households.household_id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
