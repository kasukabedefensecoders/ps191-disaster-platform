"""store curated change-detection imagery in Postgres, not MinIO

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-25

Found live: `POST /zones/{id}/change-detections/run` 400s with "no curated
before/after imagery uploaded for zone 'ZN-01' yet" on every attempt,
including right after "Reset demo data" — not because reset deletes
anything (it never touches change_detections or the image store), but
because no MinIO instance is provisioned on this deployment at all
(docs/TRD.md §11's already-recorded gap): `object_exists()` (app/storage.py)
catches any connection failure and returns False, which looks identical to
"never uploaded" from the caller's side. Re-wiring `ensure_sample_imagery_
for_zone` into the reset flow — the fix a user might reasonably expect —
would not have helped: there is nowhere for the upload to land.

Rather than provision MinIO on Railway (an infra change this session isn't
making again after the migration Custom Start Command incident, TRD §11),
this moves the one curated demo pair (two small ~200x200 grayscale PNGs)
into Postgres directly, which is already reliably present everywhere this
app runs. MinIO/app/storage.py is untouched and still what a real
`before_image_ref`/`after_image_ref` for change_detections points at (per
Backend Schema §5.12, object-storage keys); this table exists specifically
for the one hackathon-curated sample pair, not as a general MinIO
replacement.
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        create table sample_imagery (
          zone_display_code text not null,
          kind text not null check (kind in ('before', 'after')),
          content_type text not null,
          data bytea not null,
          created_at timestamptz not null default now(),
          primary key (zone_display_code, kind)
        )
        """
    )
    op.execute(f"grant select, insert, update, delete on sample_imagery to {settings.app_db_user}")


def downgrade() -> None:
    op.execute(f"revoke select, insert, update, delete on sample_imagery from {settings.app_db_user}")
    op.execute("drop table if exists sample_imagery")
