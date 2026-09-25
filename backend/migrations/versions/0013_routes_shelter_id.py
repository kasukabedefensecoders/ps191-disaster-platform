"""routes gain shelter_id — which shelter this route actually leads to

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-26

Found live, right after migration 0012 shipped: the Evacuation Routes
screen showed each zone's own route (fixed), but there was still no way to
see *which shelter* it led to — `routes` never had a `shelter_id`, only an
anonymous `dest_geom` point. That point isn't even reliably at the target
shelter's own coordinates: RT-07's dest_geom is wherever its fetched real
OSM road segment happens to end, not SH-01's literal location. Naming the
shelter was pure coincidence-of-geometry, not a real relationship.

Backfills the one pre-existing RT-07 row to SH-01 (the prototype's own
"Route RT-07 · Upper Ridge -> SH-01" label), then makes the column NOT
NULL. `app/seed.py` sets shelter_id explicitly for every route going
forward — for ZN-02/03/04 it's whichever shelter `_nearest_shelter` (added
in 0012) already picked as that route's destination.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter table routes add column shelter_id uuid references shelters(shelter_id)")
    op.execute(
        "update routes set shelter_id = (select shelter_id from shelters where display_code = 'SH-01') "
        "where display_code = 'RT-07' and shelter_id is null"
    )
    op.execute("alter table routes alter column shelter_id set not null")
    op.execute("create index idx_routes_shelter on routes(shelter_id)")


def downgrade() -> None:
    op.execute("drop index if exists idx_routes_shelter")
    op.execute("alter table routes drop column shelter_id")
