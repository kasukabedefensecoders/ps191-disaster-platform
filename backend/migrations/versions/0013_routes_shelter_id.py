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
"Route RT-07 · Upper Ridge -> SH-01" label), then falls back to nearest-
shelter-by-`dest_geom` for anything still unset — needed live because the
zone_id fix (0012) had already been followed by a data patch creating
RT-02/03/04 (as RT-8/9/10, via `POST /routes`) before this migration ran,
so RT-07 wasn't the only pre-existing row without a shelter_id. For those
three, `dest_geom` genuinely *is* the target shelter's own point (unlike
RT-07's real OSM endpoint), so nearest-by-distance recovers the exact
shelter each was created against. `app/seed.py` sets shelter_id explicitly
for every route on a fresh database, so this fallback is a live-data
safety net, not the primary path.
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
    op.execute(
        "update routes r set shelter_id = ("
        "  select s.shelter_id from shelters s order by ST_DistanceSphere(r.dest_geom, s.geom) limit 1"
        ") where shelter_id is null"
    )
    op.execute("alter table routes alter column shelter_id set not null")
    op.execute("create index idx_routes_shelter on routes(shelter_id)")


def downgrade() -> None:
    op.execute("drop index if exists idx_routes_shelter")
    op.execute("alter table routes drop column shelter_id")
