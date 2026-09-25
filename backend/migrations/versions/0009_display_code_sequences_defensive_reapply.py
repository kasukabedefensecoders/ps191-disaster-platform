"""defensively re-apply migration 0008's sequences and grants

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-25

Found live: after deploying migration 0008, every operation that calls
next_display_code() — creating a relocation, a standalone handoff, or
syncing a survey — started failing with a plain 500 on the deployed
Railway backend, across every affected prefix (SV, HH, MV, HO), even
though the rest of the app (including the unrelated forecast-model fix
from the same deploy) was confirmably running the new code. That pattern
is consistent with the sequences and/or their `app_user` grants from
migration 0008 not actually existing against the database the running
app connects to, despite `alembic upgrade head` reporting success against
the migration connection — the two use different URLs/roles
(`MIGRATION_DATABASE_URL` vs `DATABASE_URL`, Backend Schema §7), and this
migration exists because the assumption that applying DDL through one
implies it's visible through the other turned out not to hold here, for
a reason this session couldn't pin down further without direct access to
Railway's deploy logs.

This migration doesn't try to diagnose that gap further — it just redoes
migration 0008's own work idempotently (`create sequence if not exists`,
re-`setval` to the current max, re-`grant usage`), so it's a genuine fix
if 0008 silently didn't take effect, and a complete no-op if it did.
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PREFIXED_TABLES = [
    ("sv", "surveys", "display_code"),
    ("hh", "households", "display_code"),
    ("ho", "handoff_logs", "display_code"),
    ("mv", "relocation_records", "display_code"),
    ("rt", "routes", "display_code"),
]


def upgrade() -> None:
    for key, table, column in PREFIXED_TABLES:
        op.execute(f"create sequence if not exists display_code_seq_{key}")
        op.execute(
            f"""
            do $$
            declare
              cur_max bigint;
            begin
              select coalesce(max(substring({column} from '[0-9]+$')::bigint), 0)
                into cur_max
                from {table}
                where {column} ~ '^[A-Za-z]+-[0-9]+$';
              if cur_max = 0 then
                perform setval('display_code_seq_{key}', 1, false);
              else
                perform setval('display_code_seq_{key}', cur_max, true);
              end if;
            end
            $$;
            """
        )
        op.execute(f"grant usage on sequence display_code_seq_{key} to {settings.app_db_user}")


def downgrade() -> None:
    """No-op — this migration only re-asserts state 0008 already owns;
    0008's own downgrade is what actually removes the sequences/grants."""
    pass
