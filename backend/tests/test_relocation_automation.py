"""Coverage for the allocation & logistics workflow additions: auto vehicle
assignment on create, shelter-occupancy + auto-handoff generation on
arrival, field_officer being allowed to advance relocation status (but not
create), and the demo-seed endpoint."""
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


def _vehicle_id(client, headers, display_code):
    vehicles = client.get("/vehicles", headers=headers).json()
    return next(v["vehicle_id"] for v in vehicles if v["display_code"] == display_code)


def _cleanup_relocations(admin_db, record_ids, vehicle_id=None, shelter_id=None, occupancy_delta=0):
    for record_id in record_ids:
        admin_db.execute(text("delete from handoff_logs where linked_record_id = :id"), {"id": record_id})
        admin_db.execute(text("delete from audit_log where entity_id = :id"), {"id": record_id})
        admin_db.execute(text("delete from relocation_records where record_id = :id"), {"id": record_id})
    if vehicle_id is not None:
        admin_db.execute(text("update vehicles set status = 'available' where vehicle_id = :id"), {"id": vehicle_id})
    if shelter_id is not None and occupancy_delta:
        admin_db.execute(
            text("update shelters set current_occupancy = current_occupancy - :d where shelter_id = :id"),
            {"d": occupancy_delta, "id": shelter_id},
        )
    admin_db.commit()


def _cleanup_relocation(admin_db, record_id, vehicle_id=None, shelter_id=None, occupancy_delta=0):
    admin_db.execute(text("delete from handoff_logs where linked_record_id = :id"), {"id": record_id})
    admin_db.execute(text("delete from audit_log where entity_id = :id"), {"id": record_id})
    admin_db.execute(text("delete from relocation_records where record_id = :id"), {"id": record_id})
    if vehicle_id is not None:
        admin_db.execute(text("update vehicles set status = 'available' where vehicle_id = :id"), {"id": vehicle_id})
    if shelter_id is not None and occupancy_delta:
        admin_db.execute(
            text("update shelters set current_occupancy = current_occupancy - :d where shelter_id = :id"),
            {"d": occupancy_delta, "id": shelter_id},
        )
    admin_db.commit()


def test_create_relocation_without_vehicle_id_auto_assigns_best_fit(client, admin_db):
    """HH-118 (ZN-01) has population_count 3 — both seeded trucks (capacity
    18 and 24) fit, so best-fit-first should pick the smaller one."""
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    household_id = _household_id(client, headers, "ZN-01", "HH-118")
    shelter_id = _shelter_id(client, headers, "SH-01")

    response = client.post("/relocations", headers=headers, json={"household_id": household_id, "shelter_id": shelter_id})
    assert response.status_code == 201
    record = response.json()
    vehicle_id = record["vehicle_id"]

    try:
        assert vehicle_id is not None
        vehicle = client.get("/vehicles", headers=headers).json()
        picked = next(v for v in vehicle if v["vehicle_id"] == vehicle_id)
        assert picked["capacity"] == 18
    finally:
        _cleanup_relocation(admin_db, record["record_id"], vehicle_id=vehicle_id)


def test_arrival_bumps_shelter_occupancy_and_raises_handoffs_for_vulnerable_members(client, admin_db):
    """HH-112 (ZN-01): population 9 (>8), 4 children, 1 elderly — arrival
    should bump SH-01's occupancy by 9 and raise all three auto-handoff
    categories (Change 3)."""
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    household_id = _household_id(client, headers, "ZN-01", "HH-112")
    shelter_id = _shelter_id(client, headers, "SH-01")

    before_occupancy = client.get(f"/shelters/{shelter_id}", headers=headers).json()["current_occupancy"]

    created = client.post("/relocations", headers=headers, json={"household_id": household_id, "shelter_id": shelter_id})
    record_id = created.json()["record_id"]
    vehicle_id = created.json()["vehicle_id"]

    try:
        client.patch(f"/relocations/{record_id}/status", headers=headers, json={"status": "in_transit"})
        arrived = client.patch(f"/relocations/{record_id}/status", headers=headers, json={"status": "arrived"})
        assert arrived.status_code == 200

        after_occupancy = client.get(f"/shelters/{shelter_id}", headers=headers).json()["current_occupancy"]
        assert after_occupancy == before_occupancy + 9

        handoffs = client.get("/handoffs", headers=headers, params={"limit": 200}).json()["items"]
        linked = [h for h in handoffs if h["linked_record_id"] == record_id]
        assert {h["need_type"] for h in linked} == {
            "Child care",
            "Elderly medical assistance",
            "Logistics support — large household",
        }
    finally:
        _cleanup_relocation(admin_db, record_id, vehicle_id=vehicle_id, shelter_id=shelter_id, occupancy_delta=9)


def test_field_officer_can_advance_status_of_their_own_zone_relocation_but_not_create_one(client, admin_db):
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")

    # HH-104 is in ZN-01, one of the seeded field_officer's assigned zones.
    household_id = _household_id(client, sdma_headers, "ZN-01", "HH-104")
    shelter_id = _shelter_id(client, sdma_headers, "SH-02")
    created = client.post("/relocations", headers=sdma_headers, json={"household_id": household_id, "shelter_id": shelter_id})
    record_id = created.json()["record_id"]
    vehicle_id = created.json()["vehicle_id"]

    try:
        # still sdma_official-only to create
        forbidden = client.post("/relocations", headers=officer_headers, json={"household_id": household_id, "shelter_id": shelter_id})
        assert forbidden.status_code == 403

        advanced = client.patch(f"/relocations/{record_id}/status", headers=officer_headers, json={"status": "in_transit"})
        assert advanced.status_code == 200
        assert advanced.json()["status"] == "in_transit"
    finally:
        _cleanup_relocation(admin_db, record_id, vehicle_id=vehicle_id)


def test_demo_seed_requires_sdma_official_and_resets_on_every_call(client, admin_db):
    """Judge-facing "Reset demo data": unlike the old seed-once-then-no-op
    behaviour, every call now tears down relocation_records/surveys (plus
    the vehicle/shelter fields their lifecycle mutates) and reseeds fresh —
    so a throwaway relocation made before the call must be gone afterward,
    replaced by exactly the 11-household/8-survey demo plan, and a second
    call must land on that same fresh state again rather than erroring or
    piling up duplicates."""
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    assert client.post("/demo/seed-relocations", headers=officer_headers).status_code == 403

    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")

    household_id = _household_id(client, sdma_headers, "ZN-01", "HH-118")
    shelter_id = _shelter_id(client, sdma_headers, "SH-01")
    created = client.post("/relocations", headers=sdma_headers, json={"household_id": household_id, "shelter_id": shelter_id})
    throwaway_record_id = created.json()["record_id"]

    try:
        first = client.post("/demo/seed-relocations", headers=sdma_headers)
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["created"] is True
        assert len(first_body["items"]) == 11
        assert len(first_body["surveys"]) == 8
        assert throwaway_record_id not in {item["record_id"] for item in first_body["items"]}

        # A second call must reset and reproduce the same fresh state, not
        # error (FK violation on handoff_logs/incident_outcomes) or double
        # up (23 relocations, 16 surveys).
        second = client.post("/demo/seed-relocations", headers=sdma_headers)
        assert second.status_code == 200
        second_body = second.json()
        assert len(second_body["items"]) == 11
        assert len(second_body["surveys"]) == 8
    finally:
        admin_db.execute(text("delete from incident_outcomes where relocation_record_id in (select record_id from relocation_records)"))
        admin_db.execute(text("delete from handoff_logs where linked_record_id in (select record_id from relocation_records)"))
        admin_db.execute(text("delete from audit_log where entity_type = 'relocation_records'"))
        admin_db.execute(text("delete from relocation_records"))
        admin_db.execute(text("delete from surveys"))
        admin_db.execute(text("update vehicles set status = 'available' where status != 'unavailable'"))
        # app/seed.py's own SHELTERS baseline occupancy, restored the same
        # way services/demo_seed.py's own reset does.
        for code, occupancy in [("SH-01", 180), ("SH-02", 95), ("SH-03", 120), ("SH-04", 148), ("SH-05", 0)]:
            admin_db.execute(
                text("update shelters set current_occupancy = :occ where display_code = :code"),
                {"occ": occupancy, "code": code},
            )
        admin_db.commit()


def test_multiple_households_can_share_one_vehicle_within_capacity(client, admin_db):
    """Change 3's bus consolidation: BUS-01 has capacity 50. HH-112 (pop 9)
    and HH-104 (pop 6) both explicitly booked onto it must both succeed —
    the old one-relocation-per-vehicle 'available' check would have
    rejected the second booking outright."""
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    bus_id = _vehicle_id(client, headers, "BUS-01")
    shelter_id = _shelter_id(client, headers, "SH-01")
    hh112 = _household_id(client, headers, "ZN-01", "HH-112")
    hh104 = _household_id(client, headers, "ZN-01", "HH-104")

    record_ids = []
    try:
        first = client.post("/relocations", headers=headers, json={"household_id": hh112, "shelter_id": shelter_id, "vehicle_id": bus_id})
        assert first.status_code == 201
        record_ids.append(first.json()["record_id"])

        second = client.post("/relocations", headers=headers, json={"household_id": hh104, "shelter_id": shelter_id, "vehicle_id": bus_id})
        assert second.status_code == 201
        record_ids.append(second.json()["record_id"])

        bus = client.get("/vehicles", headers=headers).json()
        bus_row = next(v for v in bus if v["vehicle_id"] == bus_id)
        assert bus_row["status"] == "assigned"  # occupied, but not 'unavailable' to further bookings
    finally:
        _cleanup_relocations(admin_db, record_ids, vehicle_id=bus_id)


def test_vehicle_over_capacity_is_rejected_with_400(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    bus_id = _vehicle_id(client, headers, "BUS-02")  # capacity 50
    shelter_id = _shelter_id(client, headers, "SH-02")
    hh112 = _household_id(client, headers, "ZN-01", "HH-112")  # pop 9

    record_ids = []
    try:
        first = client.post("/relocations", headers=headers, json={"household_id": hh112, "shelter_id": shelter_id, "vehicle_id": bus_id})
        assert first.status_code == 201
        record_ids.append(first.json()["record_id"])

        # need=45 pushes 9 (already committed) + 45 over BUS-02's capacity of 50
        over_capacity = client.post(
            "/relocations",
            headers=headers,
            json={"household_id": hh112, "shelter_id": shelter_id, "vehicle_id": bus_id, "need": 45},
        )
        assert over_capacity.status_code == 400
        assert "over capacity" in over_capacity.json()["detail"]
    finally:
        _cleanup_relocations(admin_db, record_ids, vehicle_id=bus_id)


def test_vehicle_stays_in_transit_until_every_household_on_it_has_arrived(client, admin_db):
    """The bus itself must not free up (status -> 'available') while any
    household on it is still riding, even though relocation_records are
    updated one at a time — the vehicle's status is derived from the whole
    manifest (services/relocations.py's _recompute_vehicle_status)."""
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    bus_id = _vehicle_id(client, headers, "BUS-03")
    shelter_id = _shelter_id(client, headers, "SH-03")
    hh219 = _household_id(client, headers, "ZN-02", "HH-219")
    hh211 = _household_id(client, headers, "ZN-02", "HH-211")

    record_ids = []
    try:
        r1 = client.post("/relocations", headers=headers, json={"household_id": hh219, "shelter_id": shelter_id, "vehicle_id": bus_id})
        r2 = client.post("/relocations", headers=headers, json={"household_id": hh211, "shelter_id": shelter_id, "vehicle_id": bus_id})
        record_ids = [r1.json()["record_id"], r2.json()["record_id"]]

        client.patch(f"/relocations/{record_ids[0]}/status", headers=headers, json={"status": "in_transit"})
        client.patch(f"/relocations/{record_ids[1]}/status", headers=headers, json={"status": "in_transit"})

        # Only the first household arrives — the bus is still carrying the second.
        arrived_one = client.patch(f"/relocations/{record_ids[0]}/status", headers=headers, json={"status": "arrived"})
        assert arrived_one.status_code == 200
        bus_mid = next(v for v in client.get("/vehicles", headers=headers).json() if v["vehicle_id"] == bus_id)
        assert bus_mid["status"] == "in_transit"

        # Second (and last) household arrives — now the bus frees up.
        arrived_two = client.patch(f"/relocations/{record_ids[1]}/status", headers=headers, json={"status": "arrived"})
        assert arrived_two.status_code == 200
        bus_done = next(v for v in client.get("/vehicles", headers=headers).json() if v["vehicle_id"] == bus_id)
        assert bus_done["status"] == "available"

        # GET /relocations/by-vehicle groups both households under BUS-03,
        # both 'arrived', with occupancy summed across the whole manifest.
        grouped = client.get("/relocations/by-vehicle", headers=headers).json()["items"]
        bus_group = next(g for g in grouped if g["vehicle_id"] == bus_id)
        assert bus_group["status"] == "arrived"
        assert len(bus_group["households"]) == 2
        assert bus_group["current_occupancy"] == 2 + 5  # HH-219 + HH-211 population
    finally:
        occupancy_delta = 2 + 5  # both households' population, bumped onto SH-03 on arrival
        _cleanup_relocations(admin_db, record_ids, vehicle_id=bus_id, shelter_id=shelter_id, occupancy_delta=occupancy_delta)
