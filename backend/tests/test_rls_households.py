"""RLS regression test — per docs/BUILD-PLAN.md Phase 1's explicit risk note,
this exists before anything is built on top of the household/zone RLS
policies, not as end-of-phase polish.

Requires a running Postgres with migrations applied and `python -m app.seed`
already run (docker compose exec backend alembic upgrade head && python -m
app.seed) — this is an integration test against real Postgres RLS, not a
mock, since RLS enforcement is exactly the thing under test.
"""
from sqlalchemy import select

from app.auth.security import decode_token
from app.db import set_role_context
from app.models import Household, Zone

from .conftest import login


def _role_and_user_id(access_token: str) -> tuple[str, str]:
    payload = decode_token(access_token)
    return payload["role"], payload["sub"]


def test_field_officer_only_sees_households_in_assigned_zones(client, db):
    tokens = login(client, "field.officer@ps191.dev")
    role, user_id = _role_and_user_id(tokens["access_token"])
    assert role == "field_officer"

    set_role_context(db, role, user_id)
    zone_ids = {h.zone_id for h in db.scalars(select(Household))}
    zone_codes = {z.display_code for z in db.scalars(select(Zone).where(Zone.zone_id.in_(zone_ids)))}

    assert zone_codes == {"ZN-01", "ZN-03"}
    assert zone_codes.isdisjoint({"ZN-02", "ZN-04"})


def test_field_officer_only_sees_assigned_zones(client, db):
    tokens = login(client, "field.officer@ps191.dev")
    role, user_id = _role_and_user_id(tokens["access_token"])

    set_role_context(db, role, user_id)
    visible = {z.display_code for z in db.scalars(select(Zone))}

    assert visible == {"ZN-01", "ZN-03"}


def test_sdma_official_sees_all_households_and_zones(client, db):
    tokens = login(client, "sdma.official@ps191.dev")
    role, user_id = _role_and_user_id(tokens["access_token"])
    assert role == "sdma_official"

    set_role_context(db, role, user_id)
    assert len(list(db.scalars(select(Zone)))) == 4
    assert len(list(db.scalars(select(Household)))) == 11
