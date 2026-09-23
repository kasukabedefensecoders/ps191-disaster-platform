"""grant app_user DELETE on risk_forecasts

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-18

"Reset demo data" now also resets the 72-hour forecast: the "Generate"
button's per-cycle rainfall jitter (services/forecasts.py) means each click
produces a genuinely different score, so a judge who's clicked it a few
times needs a way back to "no forecast cycle run yet" without waiting for a
full app.seed reseed. That means deleting risk_forecasts rows, which — like
the four tables migration 0006 covers — app_user has no DELETE grant on yet
(migration 0002 only ever granted select/insert/update).
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(f"grant delete on risk_forecasts to {settings.app_db_user}")


def downgrade() -> None:
    op.execute(f"revoke delete on risk_forecasts from {settings.app_db_user}")
