from datetime import datetime

from sqlalchemy import LargeBinary, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SampleImagery(Base):
    """The one curated before/after change-detection pair per zone, stored
    directly in Postgres rather than MinIO (migration 0010 — see its own
    docstring: no MinIO instance is provisioned on the live deployment)."""

    __tablename__ = "sample_imagery"

    zone_display_code: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
