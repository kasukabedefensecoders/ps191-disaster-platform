"""routes gain zone_id — one evacuation route per zone, not one unscoped route

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-26

Found live: the "Evacuation routes" screen showed the same route (the one
seeded RT-07) no matter which zone a judge was looking at — not a display
bug, but an actual data gap. `routes` had no `zone_id` at all: RT-07 is a
single real OSM road stretch seeded once (docs/BUILD-PLAN.md Phase 7), so
of course every zone saw "the same route" — there was only ever one route
in the whole system, unconnected to any zone.

Adds `zone_id` (backfilled here for the one pre-existing RT-07 row to ZN-01
— the prototype's own "Route RT-07 · Upper Ridge -> SH-01" label, Upper
Ridge being ZN-01), then makes it NOT NULL: every route from here on has to
declare which zone it's for. `app/seed.py` now seeds one route per zone
(ZN-02/03/04 get new straight-line routes to their nearest eligible
shelter, computed the same honest way `services/shelter_matching.py`
already does for households with no OSRM instance behind it); this
migration only adds the column, it doesn't insert those new rows — that's
`app.seed`'s job for a fresh database, and a one-off data patch for an
already-seeded one (same pattern as the contact_phone fix).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter table routes add column zone_id uuid references zones(zone_id)")
    op.execute(
        "update routes set zone_id = (select zone_id from zones where display_code = 'ZN-01') "
        "where display_code = 'RT-07' and zone_id is null"
    )
    op.execute("alter table routes alter column zone_id set not null")
    op.execute("create index idx_routes_zone on routes(zone_id)")


def downgrade() -> None:
    op.execute("drop index if exists idx_routes_zone")
    op.execute("alter table routes drop column zone_id")
