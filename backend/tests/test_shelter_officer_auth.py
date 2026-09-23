"""Shelter officer dashboard: code-based login (POST /auth/shelter-login),
scoped strictly to GET/PATCH /shelters/me for the one shelter whose code
was presented — see docs/TRD.md §10 for why this is a deliberately
separate, lower-trust credential from the sdma_official/field_officer/
control_room JWT flow.
"""
from .conftest import login


def _shelter_officer_headers(client, shelter_code):
    resp = client.post("/auth/shelter-login", json={"shelter_code": shelter_code})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}, resp.json()


def test_invalid_shelter_code_rejected(client):
    assert client.post("/auth/shelter-login", json={"shelter_code": "SH-DOES-NOT-EXIST"}).status_code == 401


def test_shelter_login_is_case_insensitive_and_trims_whitespace(client):
    resp = client.post("/auth/shelter-login", json={"shelter_code": "  sh-01  "})
    assert resp.status_code == 200
    assert resp.json()["display_code"] == "SH-01"


def test_shelter_officer_can_view_and_update_own_shelter_only(client, admin_db):
    headers, body = _shelter_officer_headers(client, "SH-01")
    assert body["display_code"] == "SH-01"

    me = client.get("/shelters/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["shelter_id"] == body["shelter_id"]
    original_facilities = me.json()["facilities"]

    updated = client.patch(
        "/shelters/me",
        headers=headers,
        json={"current_occupancy": 200, "needs": ["blankets"], "status": "standby", "facilities": {"water": True}},
    )
    assert updated.status_code == 200
    assert updated.json()["current_occupancy"] == 200
    assert updated.json()["needs"] == ["blankets"]
    assert updated.json()["status"] == "standby"

    # restore — every field this test touched, not just some of them, so a
    # shared dev/demo database left running after the suite doesn't end up
    # with this test's scratch values baked into seeded SH-01.
    client.patch(
        "/shelters/me",
        headers=headers,
        json={"current_occupancy": 180, "needs": [], "status": "active", "facilities": original_facilities},
    )


def test_shelter_officer_cannot_edit_registration_fields(client):
    headers, _ = _shelter_officer_headers(client, "SH-02")
    denied = client.patch("/shelters/me", headers=headers, json={"name": "Renamed"})
    assert denied.status_code == 403


def test_shelter_officer_token_cannot_list_or_reach_other_shelters(client):
    headers, body = _shelter_officer_headers(client, "SH-01")
    assert client.get("/shelters", headers=headers).status_code == 401
    other = client.post("/auth/shelter-login", json={"shelter_code": "SH-02"}).json()
    assert client.get(f"/shelters/{other['shelter_id']}", headers=headers).status_code == 401


def test_normal_user_token_cannot_call_shelters_me(client):
    tokens = login(client, "sdma.official@ps191.dev")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/shelters/me", headers=headers).status_code == 401
