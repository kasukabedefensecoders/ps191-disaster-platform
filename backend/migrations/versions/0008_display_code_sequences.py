"""replace the RLS-scoped MAX-scan display-code generator with real sequences

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-25

`next_display_code()` (services/display_codes.py) picked "next" codes by
scanning `select display_code from <table> where display_code like 'PFX-%'`
through the caller's own request-scoped `db` session — the same session
`get_scoped_db` applies RLS to. For sdma_official/control_room (who bypass
the zone filter) that scan sees every row and is fine; for a field_officer
it only sees rows in their assigned zones, so the computed "next" number
silently undercounts and collides with a real, already-existing code
created in a zone outside their assignment — a live, 100%-reproducible
failure ("duplicate key value violates unique constraint
surveys_display_code_key") found by hand-testing a real survey sync through
the deployed field PWA as a field_officer, not by reading the code. The
same scan-based approach was also a plain race condition even for a role
with full visibility: two concurrent requests can both read the same MAX
before either commits.

A real Postgres sequence per prefix fixes both problems at once — sequences
are schema objects, not subject to row-level security, and `nextval()` is
atomic regardless of concurrent callers or uncommitted rows in the same
transaction. Five prefixes are affected: surveys (SV), households (HH) —
both from the field-survey sync path — plus handoff_logs (HO),
relocation_records (MV), and routes (RT). zones/shelters/vehicles take a
caller-supplied display_code (see their POST endpoints) and never went
through next_display_code, so they need no sequence here.

Each sequence is initialized to the current maximum numeric suffix already
in use for its prefix — not started fresh at 1 — so this migration is safe
to run against a database that already has seeded/live rows using this
convention; the very next code issued continues the existing series rather
than colliding with it.
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# key, table, column — key is also the sequence name suffix
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
              -- setval's value must be >= the sequence's minvalue (1), so an
              -- empty table (cur_max=0) needs is_called=false instead — that
              -- sets the "current value" to 1 without consuming it, so the
              -- next nextval() still returns 1, same as the cur_max>0 branch
              -- returning cur_max+1.
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
    for key, _table, _column in PREFIXED_TABLES:
        op.execute(f"revoke usage on sequence display_code_seq_{key} from {settings.app_db_user}")
        op.execute(f"drop sequence if exists display_code_seq_{key}")
