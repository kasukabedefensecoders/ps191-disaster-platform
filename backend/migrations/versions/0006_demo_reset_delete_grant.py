"""grant app_user DELETE on the demo-resettable tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-18

Migration 0002 granted app_user select/insert/update on every table but no
DELETE anywhere (audit_log's own delete revoke, right below that grant, was
belt-and-braces on a privilege that was never granted in the first place).
The judge-facing "Reset demo data" action (services/demo_seed.py) needs to
delete relocation_records/surveys/handoff_logs/incident_outcomes so a
re-click always lands on the same fresh scenario, so those four tables (and
only those four — audit_log stays untouchable, per CLAUDE.md rule 2) get a
scoped DELETE grant here rather than a blanket one. RLS already covers
DELETE on relocation_records/surveys: both policies are `FOR ALL` (no FOR
clause), so the existing USING clause already governs it once the privilege
exists at the grant level.
"""
from typing import Sequence, Union

from alembic import op

from app.config import settings

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DELETE_TABLES = ["relocation_records", "surveys", "handoff_logs", "incident_outcomes"]


def upgrade() -> None:
    for table in DELETE_TABLES:
        op.execute(f"grant delete on {table} to {settings.app_db_user}")


def downgrade() -> None:
    for table in DELETE_TABLES:
        op.execute(f"revoke delete on {table} from {settings.app_db_user}")
