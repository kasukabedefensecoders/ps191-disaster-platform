import uuid

import pytest

from app.services.zones import ml_vs_gsi_divergence_note

from .conftest import delete_zone, login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_list_zones_requires_auth(client):
    response = client.get("/zones")
    assert response.status_code == 401


def test_sdma_official_sees_all_seeded_zones(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    response = client.get("/zones", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4
    codes = {z["display_code"] for z in body["items"]}
    assert codes == {"ZN-01", "ZN-02", "ZN-03", "ZN-04"}
    # rule 3: confidence state travels in every response, not just detail
    for zone in body["items"]:
        assert "data_confidence" in zone
        assert "last_verified_at" in zone


def test_field_officer_sees_only_assigned_zones_via_api(client):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    response = client.get("/zones", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert {z["display_code"] for z in body["items"]} == {"ZN-01", "ZN-03"}


def test_pagination_limit_and_next_offset(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    first = client.get("/zones", headers=headers, params={"limit": 1, "offset": 0}).json()
    assert len(first["items"]) == 1
    assert first["next_offset"] == 1

    last = client.get("/zones", headers=headers, params={"limit": 1, "offset": 3}).json()
    assert len(last["items"]) == 1
    assert last["next_offset"] is None


def test_since_filters_out_unchanged_zones(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    future = client.get("/zones", headers=headers, params={"since": "2999-01-01T00:00:00Z"}).json()
    assert future["count"] == 0
    assert future["items"] == []


def test_zone_detail_includes_incident_history_and_divergence_note(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn01 = client.get("/zones", headers=headers, params={"limit": 1}).json()["items"][0]

    detail = client.get(f"/zones/{zn01['zone_id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["incident_history"]) == 3
    assert body["incident_history"][0]["hazard_type"] == "landslide"
    assert "Very High" in body["ml_vs_gsi_divergence_note"]
    assert "High" in body["ml_vs_gsi_divergence_note"]


def test_field_officer_gets_404_not_403_for_unassigned_zone(client):
    """RLS hides out-of-scope rows the same way as nonexistent ones — the
    404 must not leak whether ZN-02 exists at all (Backend Schema §7)."""
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn02 = next(
        z for z in client.get("/zones", headers=sdma_headers).json()["items"]
        if z["display_code"] == "ZN-02"
    )

    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    response = client.get(f"/zones/{zn02['zone_id']}", headers=officer_headers)
    assert response.status_code == 404


def test_only_sdma_official_can_create_zones(client, admin_db):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    district_id = client.get("/zones", headers=sdma_headers).json()["items"][0]["district_id"]

    payload = {
        "display_code": f"ZN-TEST-{uuid.uuid4().hex[:8]}",
        "district_id": district_id,
        "name": "Test Zone",
        "geom": {"type": "Polygon", "coordinates": [[[93.0, 25.0], [93.01, 25.0], [93.01, 25.01], [93.0, 25.01], [93.0, 25.0]]]},
        "hazard_types": ["flood"],
        "population": 100,
    }

    forbidden = client.post("/zones", headers=officer_headers, json=payload)
    assert forbidden.status_code == 403

    created = client.post("/zones", headers=sdma_headers, json=payload)
    try:
        assert created.status_code == 201
        body = created.json()
        assert body["display_code"] == payload["display_code"]
        assert body["geom"]["type"] == "Polygon"

        patched = client.patch(f"/zones/{body['zone_id']}", headers=sdma_headers, json={"population": 250})
        assert patched.status_code == 200
        assert patched.json()["population"] == 250
    finally:
        delete_zone(admin_db, created.json()["zone_id"])


@pytest.mark.parametrize(
    "susceptibility_score,gsi_classification,expected_substring",
    [
        (0.91, "High", "higher"),
        (0.20, "High", "lower"),
        (0.30, "Moderate", "agrees"),
        (None, "High", None),
        (0.5, "Not-a-real-category", None),
    ],
)
def test_ml_vs_gsi_divergence_note_directions(susceptibility_score, gsi_classification, expected_substring):
    note = ml_vs_gsi_divergence_note(susceptibility_score, gsi_classification)
    if expected_substring is None:
        assert note is None
    else:
        assert expected_substring in note
