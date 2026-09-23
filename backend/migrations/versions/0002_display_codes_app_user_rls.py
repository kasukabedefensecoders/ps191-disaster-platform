"""display codes, non-superuser app_user role, RLS on zones/surveys

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-12

CLAUDE.md's working-style rule requires human-readable display codes
(ZN-01, HH-112, SH-01, MV-118, SV-4471, HO-221, RT-07) as their own column
since primary keys are UUIDs — docs/BACKEND-SCHEMA.md didn't carry that
column yet, so it's added here alongside the other Phase 1 schema work.

The Docker Compose POSTGRES_USER (ps191) is a Postgres superuser, and
superusers always bypass row-level security regardless of FORCE ROW LEVEL
SECURITY. Migration 0001's household_access policy therefore did nothing
as long as the app connects as ps191. This migration creates a dedicated
non-superuser app_user role for the FastAPI app to connect as, grants it
only what it needs, and forces RLS on households/zones/surveys so it
actually applies to that role.
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DISPLAY_CODE_TABLES = [
    ("zones", "zone_id"),
    ("households", "household_id"),
    ("shelters", "shelter_id"),
    ("relocation_records", "record_id"),
    ("surveys", "survey_id"),
    ("handoff_logs", "log_id"),
    ("routes", "route_id"),
]


def upgrade() -> None:
    for table, _pk in DISPLAY_CODE_TABLES:
        op.execute(f"alter table {table} add column display_code text unique")

    op.execute(
        f"""
        do $$
        begin
          if not exists (select from pg_roles where rolname = '{settings.app_db_user}') then
            create role {settings.app_db_user} login password '{settings.app_db_password}';
          end if;
        end
        $$;
        """
    )
    op.execute(
        f"""
        do $$
        begin
          execute format('grant connect on database %I to %I', current_database(), '{settings.app_db_user}');
        end
        $$;
        """
    )
    op.execute(f"grant usage on schema public to {settings.app_db_user}")
    op.execute(f"grant select, insert, update on all tables in schema public to {settings.app_db_user}")
    op.execute(f"revoke update, delete on audit_log from {settings.app_db_user}")

    op.execute("alter table households force row level security")

    op.execute("alter table zones enable row level security")
    op.execute("alter table zones force row level security")
    op.execute(
        """
        create policy zone_access on zones
          using (
            current_setting('app.current_role', true) in ('sdma_official', 'control_room')
            or zone_id in (
              select zone_id from user_zone_assignments
              where user_id = current_setting('app.current_user_id', true)::uuid
            )
          )
        """
    )

    op.execute("alter table surveys enable row level security")
    op.execute("alter table surveys force row level security")
    op.execute(
        """
        create policy survey_access on surveys
          using (
            current_setting('app.current_role', true) in ('sdma_official', 'control_room')
            or zone_id in (
              select zone_id from user_zone_assignments
              where user_id = current_setting('app.current_user_id', true)::uuid
            )
          )
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists survey_access on surveys")
    op.execute("alter table surveys disable row level security")

    op.execute("drop policy if exists zone_access on zones")
    op.execute("alter table zones disable row level security")

    op.execute("alter table households no force row level security")

    op.execute(f"revoke all on all tables in schema public from {settings.app_db_user}")
    op.execute(f"revoke usage on schema public from {settings.app_db_user}")
    op.execute(
        f"""
        do $$
        begin
          execute format('revoke connect on database %I from %I', current_database(), '{settings.app_db_user}');
        end
        $$;
        """
    )
    op.execute(f"drop role if exists {settings.app_db_user}")

    for table, _pk in DISPLAY_CODE_TABLES:
        op.execute(f"alter table {table} drop column if exists display_code")
