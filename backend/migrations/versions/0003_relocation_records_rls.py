"""RLS on relocation_records, joined through households -> zone assignment

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-12

A fourth table beyond the three docs/BACKEND-SCHEMA.md §7 originally named
(households, zones, surveys). relocation_records has no zone_id column of
its own, so its policy joins household_id -> households.zone_id ->
user_zone_assignments the same way surveys does, rather than repeating a
zone_id-in-assigned-zones check directly. See Backend Schema §7 for the
full rationale (Phase 6 shipped writes gated to sdma_official but left
reads unscoped; this closes that gap).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter table relocation_records enable row level security")
    op.execute("alter table relocation_records force row level security")
    op.execute(
        """
        create policy relocation_access on relocation_records
          using (
            current_setting('app.current_role', true) in ('sdma_official', 'control_room')
            or household_id in (
              select h.household_id
              from households h
              join user_zone_assignments uza on uza.zone_id = h.zone_id
              where uza.user_id = current_setting('app.current_user_id', true)::uuid
            )
          )
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists relocation_access on relocation_records")
    op.execute("alter table relocation_records disable row level security")
