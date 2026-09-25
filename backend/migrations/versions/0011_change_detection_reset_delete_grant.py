"""grant app_user DELETE on change_detections

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-25

SAR change detection (Phase 11): the frontend was showing a zone's
before/after slider and detection-result panel just because a *previous*
detection run (from an earlier demo cycle, or from another judge's click)
left a change_detections row for it — "Reset demo data" never cleared
that table, so it never got the same "back to not-run-yet" treatment
risk_forecasts got in migration 0007. Fixing that means deleting
change_detections rows on reset, which — like risk_forecasts before
migration 0007 — app_user has no DELETE grant on yet (migration 0002 only
ever granted select/insert/update).
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(f"grant delete on change_detections to {settings.app_db_user}")


def downgrade() -> None:
    op.execute(f"revoke delete on change_detections from {settings.app_db_user}")
