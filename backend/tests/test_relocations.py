"""Phase 6: relocation_records state machine, vehicle/escort assignment,
and the generic audit_log write path (docs/BUILD-PLAN.md — "every
relocation decision and every priority-ranking write needs an audit row")."""
import uuid

from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _household_id(client, headers, zone_display_code, household_display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    zone_id = next(z["zone_id"] for z in zones if z["display_code"] == zone_display_code)
    households = client.get(f"/zones/{zone_id}/households", headers=headers).json()["items"]
    return next(h["household_id"] for h in households if h["display_code"] == household_display_code)


def _shelter_id(client, headers, display_code):
    shelters = client.get("/shelters", headers=headers).json()["items"]
    return next(s["shelter_id"] for s in shelters if s["display_code"] == display_code)


def _available_vehicle_id(client, headers):
    return client.get("/vehicles", headers=headers, params={"status": "available"}).json()[0]["vehicle_id"]


def _available_escort_id(client, headers):
    return client.get("/escorts", headers=headers, params={"status": "available"}).json()[0]["escort_id"]


def test_list_relocations_requires_auth(client):
    assert client.get("/relocations").status_code == 401


def test_only_sdma_official_can_create_relocations(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")

    household_id = _household_id(client, sdma_headers, "ZN-01", "HH-112")
    shelter_id = _shelter_id(client, sdma_headers, "SH-01")
    payload = {"household_id": household_id, "shelter_id": shelter_id}

    assert client.post("/relocations", headers=officer_headers, json=payload).status_code == 403


def test_create_relocation_freezes_scores_assigns_transport_and_writes_audit_log(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    household_id = _household_id(client, headers, "ZN-01", "HH-112")
    shelter_id = _shelter_id(client, headers, "SH-01")
    vehicle_id = _available_vehicle_id(client, headers)
    escort_id = _available_escort_id(client, headers)

    payload = {"household_id": household_id, "shelter_id": shelter_id, "vehicle_id": vehicle_id, "escort_id": escort_id}
    response = client.post("/relocations", headers=headers, json=payload)
    assert response.status_code == 201
    record = response.json()

    try:
        # HH-112's priority is hand-verified at 0.81/"immediate" (test_scoring.py)
        assert record["priority_tier"] == "immediate"
        assert record["priority_factors"] is not None and len(record["priority_factors"]) == 5
        assert record["allocation_factors"] is not None and len(record["allocation_factors"]) == 5
        assert record["status"] == "assigned"
        assert record["display_code"].startswith("MV-")

        # vehicle/escort move out of the available pool
        vehicles = client.get("/vehicles", headers=headers, params={"status": "available"}).json()
        assert vehicle_id not in {v["vehicle_id"] for v in vehicles}
        escorts = client.get("/escorts", headers=headers, params={"status": "available"}).json()
        assert escort_id not in {e["escort_id"] for e in escorts}

        # rule 2: the decision itself is captured in the append-only audit log
        row = admin_db.execute(
            text("select action_type, entity_type, entity_id, factors_snapshot from audit_log where entity_id = :id"),
            {"id": record["record_id"]},
        ).mappings().one()
        assert row["action_type"] == "relocation_decided"
        assert row["entity_type"] == "relocation_records"
        assert row["factors_snapshot"]["priority_tier"] == "immediate"
        assert row["factors_snapshot"]["vehicle_id"] == vehicle_id
    finally:
        admin_db.execute(text("delete from audit_log where entity_id = :id"), {"id": record["record_id"]})
        admin_db.execute(text("delete from relocation_records where record_id = :id"), {"id": record["record_id"]})
        admin_db.execute(text("update vehicles set status = 'available' where vehicle_id = :id"), {"id": vehicle_id})
        admin_db.execute(text("update escorts set status = 'available' where escort_id = :id"), {"id": escort_id})
        admin_db.commit()


def test_unavailable_vehicle_is_rejected_with_400(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    household_id = _household_id(client, headers, "ZN-01", "HH-104")
    shelter_id = _shelter_id(client, headers, "SH-02")
    vehicle_id = _available_vehicle_id(client, headers)

    admin_db.execute(text("update vehicles set status = 'unavailable' where vehicle_id = :id"), {"id": vehicle_id})
    admin_db.commit()
    try:
        payload = {"household_id": household_id, "shelter_id": shelter_id, "vehicle_id": vehicle_id}
        response = client.post("/relocations", headers=headers, json=payload)
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]
    finally:
        admin_db.execute(text("update vehicles set status = 'available' where vehicle_id = :id"), {"id": vehicle_id})
        admin_db.commit()


def test_status_transitions_are_forward_only_and_free_transport_on_arrival(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    household_id = _household_id(client, headers, "ZN-01", "HH-107")
    shelter_id = _shelter_id(client, headers, "SH-03")
    vehicle_id = _available_vehicle_id(client, headers)

    created = client.post(
        "/relocations", headers=headers, json={"household_id": household_id, "shelter_id": shelter_id, "vehicle_id": vehicle_id}
    ).json()
    record_id = created["record_id"]

    try:
        # can't skip straight to arrived
        skip = client.patch(f"/relocations/{record_id}/status", headers=headers, json={"status": "arrived"})
        assert skip.status_code == 400

        in_transit = client.patch(f"/relocations/{record_id}/status", headers=headers, json={"status": "in_transit"})
        assert in_transit.status_code == 200
        body = in_transit.json()
        assert body["status"] == "in_transit"
        assert body["in_transit_at"] is not None

        vehicle_mid = client.get("/vehicles", headers=headers, params={"status": "in_transit"}).json()
        assert vehicle_id in {v["vehicle_id"] for v in vehicle_mid}

        # can't go backward
        backward = client.patch(f"/relocations/{record_id}/status", headers=headers, json={"status": "assigned"})
        assert backward.status_code == 400

        arrived = client.patch(f"/relocations/{record_id}/status", headers=headers, json={"status": "arrived"})
        assert arrived.status_code == 200
        assert arrived.json()["arrived_at"] is not None

        vehicle_final = client.get("/vehicles", headers=headers, params={"status": "available"}).json()
        assert vehicle_id in {v["vehicle_id"] for v in vehicle_final}
    finally:
        # Arrival also bumped SH-03's occupancy by HH-107's population_count
        # and auto-raised handoffs for its children/elderly (Change 3) —
        # both need undoing too, or they outlive this test.
        admin_db.execute(text("delete from handoff_logs where linked_record_id = :id"), {"id": record_id})
        admin_db.execute(
            text("update shelters set current_occupancy = current_occupancy - 4 where shelter_id = :id"),
            {"id": shelter_id},
        )
        admin_db.execute(text("delete from audit_log where entity_id = :id"), {"id": record_id})
        admin_db.execute(text("delete from relocation_records where record_id = :id"), {"id": record_id})
        admin_db.execute(text("update vehicles set status = 'available' where vehicle_id = :id"), {"id": vehicle_id})
        admin_db.commit()


def test_unknown_relocation_returns_404(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    response = client.get(f"/relocations/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_field_officer_cannot_read_relocation_outside_assigned_zones(client, admin_db):
    """RLS on relocation_records (Backend Schema §7, migration 0003) joins
    household_id -> households.zone_id -> user_zone_assignments, the same
    way surveys does — relocation_records has no zone_id column of its own.
    Writes were already gated to sdma_official (Phase 6); this closes the
    read side: a field_officer must get nothing back for a record tied to
    a household outside their assigned zones, not just be blocked from
    creating one."""
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")

    # HH-203 is in ZN-02, not one of the seeded field_officer's assigned
    # zones (ZN-01, ZN-03) — sdma_official bypasses RLS and can decide it.
    household_id = _household_id(client, sdma_headers, "ZN-02", "HH-203")
    shelter_id = _shelter_id(client, sdma_headers, "SH-02")
    created = client.post(
        "/relocations", headers=sdma_headers, json={"household_id": household_id, "shelter_id": shelter_id}
    )
    assert created.status_code == 201
    record_id = created.json()["record_id"]
    # No vehicle_id was passed, so create_relocation auto-assigned whatever
    # was available (Change 2's auto vehicle assignment) — release it too,
    # or it stays stuck "assigned" for the rest of the test session with
    # only 2 seeded trucks to go around.
    vehicle_id = created.json()["vehicle_id"]

    try:
        # sdma_official (bypasses RLS) can still see it.
        assert client.get(f"/relocations/{record_id}", headers=sdma_headers).status_code == 200

        # field_officer gets nothing — same 404-hides-existence pattern as
        # zones/households, not a 403 that would confirm the record exists.
        hidden = client.get(f"/relocations/{record_id}", headers=officer_headers)
        assert hidden.status_code == 404

        officer_list = client.get("/relocations", headers=officer_headers).json()
        assert record_id not in {r["record_id"] for r in officer_list["items"]}
    finally:
        admin_db.execute(text("delete from audit_log where entity_id = :id"), {"id": record_id})
        admin_db.execute(text("delete from relocation_records where record_id = :id"), {"id": record_id})
        if vehicle_id is not None:
            admin_db.execute(text("update vehicles set status = 'available' where vehicle_id = :id"), {"id": vehicle_id})
        admin_db.commit()
