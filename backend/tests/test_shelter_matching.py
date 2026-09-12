"""Phase 5: GET /households/{id}/shelter-matches wires matchFactors()/
matchScore() into a real endpoint. Distances come from real PostGIS
geometry (ST_DistanceSphere), not a hand-computed fixture like Phase 2's
prototype-reproduction tests — hardcoding an "expected" geodetic distance
here would just re-implement ST_DistanceSphere in Python and be exactly
the kind of fragile duplication the actual number doesn't need. So these
check structural invariants and relative ordering instead of exact scores.
"""
import pytest

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _household_id(client, headers, zone_display_code, household_display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    zone_id = next(z["zone_id"] for z in zones if z["display_code"] == zone_display_code)
    households = client.get(f"/zones/{zone_id}/households", headers=headers).json()["items"]
    return next(h["household_id"] for h in households if h["display_code"] == household_display_code)


def test_requires_auth(client):
    assert client.get("/households/00000000-0000-0000-0000-000000000000/shelter-matches").status_code == 401


def test_unknown_household_returns_404(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    response = client.get("/households/00000000-0000-0000-0000-000000000000/shelter-matches", headers=headers)
    assert response.status_code == 404


def test_field_officer_cannot_match_shelters_for_unassigned_household(client):
    """RLS on households (Backend Schema §7) scopes this endpoint too: a
    field_officer can't match shelters for a household outside their
    assigned zones — same 404-hides-existence pattern as everywhere else."""
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")

    # HH-203 is in ZN-02, not assigned to the seeded field_officer.
    hh203_id = _household_id(client, sdma_headers, "ZN-02", "HH-203")
    response = client.get(f"/households/{hh203_id}/shelter-matches", headers=officer_headers)
    assert response.status_code == 404


def test_ranked_matches_are_sorted_descending_and_shaped_correctly(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    hh112_id = _household_id(client, headers, "ZN-01", "HH-112")

    response = client.get(f"/households/{hh112_id}/shelter-matches", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["need"] == 9  # HH-112's population_count, default when `need` omitted
    assert body["count"] == 5  # none of the 5 seeded shelters are closed/damaged
    assert "straight-line" in body["note"]

    scores = [m["match_score"] for m in body["items"]]
    assert scores == sorted(scores, reverse=True)

    for match in body["items"]:
        assert set(match["match_factors"][0].keys()) == {"name", "weight", "input_value", "contribution"}
        assert match["distance_km"] > 0
        assert match["route_access"] == "clear"


def test_need_override_changes_remaining_capacity_factor(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    hh112_id = _household_id(client, headers, "ZN-01", "HH-112")

    small_need = client.get(f"/households/{hh112_id}/shelter-matches", headers=headers, params={"need": 1}).json()
    large_need = client.get(f"/households/{hh112_id}/shelter-matches", headers=headers, params={"need": 100}).json()

    sh01_small = next(m for m in small_need["items"] if m["display_code"] == "SH-01")
    sh01_large = next(m for m in large_need["items"] if m["display_code"] == "SH-01")
    assert sh01_small["match_score"] > sh01_large["match_score"]


def test_nearby_shelters_beat_a_far_one_on_distance(client):
    """SH-03 and SH-01 sit within ~1km of ZN-01 (real seeded coordinates);
    SH-04 sits ~45km away on the other side of the district — real PostGIS
    geometry, not a hardcoded fixture, so only the ordering is asserted."""
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    hh112_id = _household_id(client, headers, "ZN-01", "HH-112")

    items = client.get(f"/households/{hh112_id}/shelter-matches", headers=headers).json()["items"]
    by_code = {m["display_code"]: m for m in items}

    assert by_code["SH-01"]["distance_km"] < by_code["SH-04"]["distance_km"]
    assert by_code["SH-03"]["distance_km"] < by_code["SH-04"]["distance_km"]


def test_closed_or_damaged_shelters_are_excluded(client, admin_db):
    from sqlalchemy import text

    headers = _auth_headers(client, "sdma.official@ps191.dev")
    hh112_id = _household_id(client, headers, "ZN-01", "HH-112")

    admin_db.execute(text("update shelters set status = 'closed' where display_code = 'SH-05'"))
    admin_db.commit()
    try:
        items = client.get(f"/households/{hh112_id}/shelter-matches", headers=headers).json()["items"]
        assert "SH-05" not in {m["display_code"] for m in items}
    finally:
        admin_db.execute(text("update shelters set status = 'active' where display_code = 'SH-05'"))
        admin_db.commit()
