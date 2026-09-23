"""vehicles gain display_code and route_label

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-18

The Logistics Tracker's bus-consolidation view (task-given spec) needs a
human-readable vehicle identifier ("BUS-01") and a rider-facing route name
("Ridge Route") to show on a per-vehicle card. CLAUDE.md's display-code list
deliberately left vehicles out ("referenced by UUID only") back when a
relocation record mapped 1:1 to a vehicle and nothing user-facing ever
needed to name one — that assumption no longer holds now that several
relocation_records share one vehicle_id and the UI groups by vehicle, so
vehicles join the same human-readable-code convention as every other
display-facing entity (Backend Schema §2). route_label is separate from
vehicle_type (Bus/Truck) — it names the run ("Ridge Route"), not the
vehicle class — and stays nullable since not every vehicle (an ad hoc
truck) is assigned to a named route.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("display_code", sa.Text(), nullable=True))
    op.add_column("vehicles", sa.Column("route_label", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_vehicles_display_code", "vehicles", ["display_code"])


def downgrade() -> None:
    op.drop_constraint("uq_vehicles_display_code", "vehicles", type_="unique")
    op.drop_column("vehicles", "route_label")
    op.drop_column("vehicles", "display_code")
