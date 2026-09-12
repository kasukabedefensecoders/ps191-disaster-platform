"""Phase 4: GET /zones/{id}/households wires Phase 2's scoring functions
into a real, RLS-scoped, ranked endpoint. Reuses test_scoring.py's
hand-computed EXPECTED table as the source of truth for per-household
scores, rather than re-deriving them, so there's one place those numbers
are verified against the prototype's own arithmetic."""
import pytest

from .conftest import login
from .test_scoring import EXPECTED


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _zone_id_by_code(client, headers, display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    return next(z["zone_id"] for z in zones if z["display_code"] == display_code)


def test_requires_auth(client):
    response = client.get("/zones/00000000-0000-0000-0000-000000000000/households")
    assert response.status_code == 401


def test_ranked_list_matches_hand_computed_scores_and_is_sorted_descending(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id_by_code(client, headers, "ZN-01")

    response = client.get(f"/zones/{zone_id}/households", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4  # HH-112, HH-104, HH-107, HH-118

    items = body["items"]
    codes_in_order = [h["display_code"] for h in items]
    assert codes_in_order == sorted(
        codes_in_order, key=lambda c: EXPECTED[c][1], reverse=True
    ), "ranked list must be sorted by priority_score descending"

    for household in items:
        expected_vuln, expected_prio, expected_tier = EXPECTED[household["display_code"]]
        assert household["vulnerability_score"] == pytest.approx(expected_vuln, abs=1e-9)
        assert household["priority_score"] == pytest.approx(expected_prio, abs=1e-9)
        assert household["priority_tier"] == expected_tier
        assert set(household["vulnerability_factors"][0].keys()) == {"name", "weight", "input_value", "contribution"}
        assert set(household["priority_factors"][0].keys()) == {"name", "weight", "input_value", "contribution"}
        assert "data_confidence" in household
        assert "last_surveyed_at" in household


def test_field_officer_only_ranks_their_assigned_zones_households(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")

    zn01_id = _zone_id_by_code(client, sdma_headers, "ZN-01")
    ok = client.get(f"/zones/{zn01_id}/households", headers=officer_headers)
    assert ok.status_code == 200
    assert {h["display_code"] for h in ok.json()["items"]} == {"HH-112", "HH-104", "HH-107", "HH-118"}

    zn02_id = _zone_id_by_code(client, sdma_headers, "ZN-02")
    hidden = client.get(f"/zones/{zn02_id}/households", headers=officer_headers)
    assert hidden.status_code == 404


def test_unknown_zone_id_returns_404(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    response = client.get("/zones/00000000-0000-0000-0000-000000000000/households", headers=headers)
    assert response.status_code == 404
