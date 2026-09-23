"""shelter_status gains 'standby'; shelters gain contact_name/contact_phone/needs

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17

The Shelter Registration & Management dashboard (task-given spec) needs a
status distinct from the existing active/full/closed/damaged set: a shelter
that is stood up and ready but not currently housing anyone, matching the
prototype's own "SH-05 moved from standby to active roster" note (dc.html)
even though the prototype's seed data never wired that status through to
docs/BACKEND-SCHEMA.md §5.5's enum. 'full'/'damaged' stay in the enum for
other/future automatic use; the registration form's dropdown only offers
active/standby/closed.

contact_name/contact_phone and needs (a free-form jsonb array of urgent-need
tags, e.g. ["medical", "blankets"]) are new columns the schema had no home
for — the registration form and the needs-summary panel both need them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter type shelter_status add value if not exists 'standby'")
    op.add_column("shelters", sa.Column("contact_name", sa.Text(), nullable=True))
    op.add_column("shelters", sa.Column("contact_phone", sa.Text(), nullable=True))
    op.add_column(
        "shelters",
        sa.Column("needs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("shelters", "needs")
    op.drop_column("shelters", "contact_phone")
    op.drop_column("shelters", "contact_name")
    # Postgres has no "drop enum value" — a shelter row left in 'standby'
    # status would block recreating a narrower type, so removing the value
    # here isn't attempted; this matches how 0001's own down_revision never
    # has to handle a value some other migration added mid-stream.
