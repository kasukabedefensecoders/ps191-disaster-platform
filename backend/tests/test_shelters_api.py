import uuid

from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_list_shelters_requires_auth(client):
    assert client.get("/shelters").status_code == 401


def test_field_officer_sees_all_shelters_no_rls(client):
    """Shelters carry no RLS (Backend Schema §7) — unlike zones/households,
    every authenticated role sees the same 5 seeded shelters."""
    headers = _auth_headers(client, "field.officer@ps191.dev")
    response = client.get("/shelters", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 5
    assert {s["display_code"] for s in body["items"]} == {"SH-01", "SH-02", "SH-03", "SH-04", "SH-05"}


def test_only_sdma_official_can_create_and_update_shelters(client, admin_db):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    district_id = client.get("/shelters", headers=sdma_headers).json()["items"][0]["district_id"]

    payload = {
        "display_code": f"SH-TEST-{uuid.uuid4().hex[:8]}",
        "district_id": district_id,
        "name": "Test Shelter",
        "geom": {"type": "Point", "coordinates": [93.05, 25.15]},
        "max_capacity": 100,
        "current_occupancy": 10,
        "facilities": {"water": True},
    }

    assert client.post("/shelters", headers=officer_headers, json=payload).status_code == 403

    created = client.post("/shelters", headers=sdma_headers, json=payload)
    try:
        assert created.status_code == 201
        body = created.json()
        assert body["geom"]["type"] == "Point"

        patched = client.patch(f"/shelters/{body['shelter_id']}", headers=sdma_headers, json={"current_occupancy": 50})
        assert patched.status_code == 200
        assert patched.json()["current_occupancy"] == 50
    finally:
        admin_db.execute(text("delete from shelters where shelter_id = :id"), {"id": created.json()["shelter_id"]})
        admin_db.commit()


def test_field_officer_cannot_write_shelters_at_all(client):
    """Shelter management is sdma_official (registration/oversight) and each
    shelter's own officer (POST /auth/shelter-login, PATCH /shelters/me)
    only. field_officer previously had a narrow occupancy/needs edit here,
    now retired now that the shelter officer dashboard owns that data."""
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    shelter = client.get("/shelters", headers=officer_headers).json()["items"][0]
    denied = client.patch(
        f"/shelters/{shelter['shelter_id']}",
        headers=officer_headers,
        json={"current_occupancy": shelter["current_occupancy"]},
    )
    assert denied.status_code == 403


def test_control_room_cannot_write_shelters(client):
    control_headers = _auth_headers(client, "control.room@ps191.dev")
    shelter = client.get("/shelters", headers=control_headers).json()["items"][0]
    assert client.patch(f"/shelters/{shelter['shelter_id']}", headers=control_headers, json={"current_occupancy": 1}).status_code == 403


def test_create_shelter_accepts_standby_status_contact_and_needs(client, admin_db):
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    district_id = client.get("/shelters", headers=sdma_headers).json()["items"][0]["district_id"]

    payload = {
        "display_code": f"SH-TEST-{uuid.uuid4().hex[:8]}",
        "district_id": district_id,
        "name": "Standby Test Shelter",
        "geom": {"type": "Point", "coordinates": [93.05, 25.15]},
        "max_capacity": 100,
        "current_occupancy": 0,
        "facilities": {"water": True, "power": True},
        "status": "standby",
        "contact_name": "Test Contact",
        "contact_phone": "+91 90000 00000",
        "needs": ["food"],
    }
    created = client.post("/shelters", headers=sdma_headers, json=payload)
    try:
        assert created.status_code == 201
        body = created.json()
        assert body["status"] == "standby"
        assert body["contact_name"] == "Test Contact"
        assert body["needs"] == ["food"]
    finally:
        admin_db.execute(text("delete from shelters where shelter_id = :id"), {"id": created.json()["shelter_id"]})
        admin_db.commit()


def test_occupancy_over_capacity_returns_400_not_500(client, admin_db):
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    district_id = client.get("/shelters", headers=sdma_headers).json()["items"][0]["district_id"]

    payload = {
        "display_code": f"SH-TEST-{uuid.uuid4().hex[:8]}",
        "district_id": district_id,
        "name": "Overfull Shelter",
        "geom": {"type": "Point", "coordinates": [93.05, 25.15]},
        "max_capacity": 10,
        "current_occupancy": 20,
    }
    response = client.post("/shelters", headers=sdma_headers, json=payload)
    assert response.status_code == 400
    assert "max_capacity" in response.json()["detail"]
