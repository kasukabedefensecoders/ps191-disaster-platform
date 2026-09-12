"""Pins the exact bug Phase 3 found while wiring zone creation: set_config's
is_local argument controls whether app.current_role/current_user_id survive
a commit. true (transaction-local) resets after the first commit in a
request; false (session-scoped) doesn't. See app/db.py's set_role_context
docstring and docs/BACKEND-SCHEMA.md §7 for the full story."""
from sqlalchemy import select, text

from app.db import set_role_context
from app.models import Zone


def test_role_context_survives_a_commit(db):
    set_role_context(db, "sdma_official", "00000000-0000-0000-0000-000000000000")
    db.execute(text("select 1"))
    db.commit()

    # A second, RLS-sensitive query in the same session, after a commit,
    # must still see zones — not none, as it would if the role context had
    # reset along with the transaction.
    zone = db.scalar(select(Zone).limit(1))
    assert zone is not None
