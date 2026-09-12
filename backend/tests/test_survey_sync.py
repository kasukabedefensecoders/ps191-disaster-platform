"""Phase 9: rule 5 (offline-first is a data-model property) and the risk
docs/BUILD-PLAN.md calls out explicitly — "the idempotent-upsert-on-retry
behavior is easy to get right in the happy path and wrong under an actual
retried failure." These tests exercise a genuine retry (the exact same
survey_id resent, simulating a dropped connection after the server had
already succeeded), not just a clean single submit.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _zone_id(client, headers, display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    return next(z["zone_id"] for z in zones if z["display_code"] == display_code)


def _household_id(client, headers, zone_display_code, household_display_code):
    zone_id = _zone_id(client, headers, zone_display_code)
    households = client.get(f"/zones/{zone_id}/households", headers=headers).json()["items"]
    return next(h["household_id"] for h in households if h["display_code"] == household_display_code)


# Original seed.py HOUSEHOLDS values for every household these tests sync
# over, keyed by display_code: (population, children, elderly, assistance,
# structural_condition). Every test that mutates one of these via the sync
# endpoint MUST restore it in a finally block via _restore_household — other
# test modules (test_household_ranking, test_shelter_matching, test_dashboard)
# assert against these exact seeded values and don't re-seed between tests.
ORIGINAL_HOUSEHOLD_VALUES = {
    "HH-104": (6, 2, 1, 1, "Kutcha"),
    "HH-107": (4, 1, 2, 0, "Semi-pucca"),
    "HH-112": (9, 4, 1, 2, "Kutcha"),
    "HH-118": (3, 0, 0, 0, "Pucca"),
}


def _restore_household(admin_db, household_id, display_code):
    pop, children, elderly, assist, structural = ORIGINAL_HOUSEHOLD_VALUES[display_code]
    admin_db.execute(
        text(
            "update households set population_count=:pop, children_count=:ch, elderly_count=:eld, "
            "assistance_needs_count=:asst, structural_condition=:structural, data_confidence='field_verified' "
            "where household_id=:id"
        ),
        {"pop": pop, "ch": children, "eld": elderly, "asst": assist, "structural": structural, "id": household_id},
    )
    admin_db.commit()


def _payload_item(survey_id, zone_id, household_id=None, geotag=None, **overrides):
    item = {
        "survey_id": survey_id,
        "zone_id": zone_id,
        "household_id": household_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "population_count": 6,
            "children_count": 2,
            "elderly_count": 1,
            "assistance_needs_count": 1,
            "structural_condition": "Semi-pucca",
            "notes": "Roof damage visible on north side",
        },
        "geotag": geotag,
    }
    item.update(overrides)
    return item


def test_sync_requires_auth(client):
    assert client.post("/surveys/sync", json={"surveys": []}).status_code == 401


def test_sync_updates_existing_household_and_defaults_review_unreviewed(client, admin_db):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    household_id = _household_id(client, headers, "ZN-01", "HH-118")  # currently Pucca, pop 3
    survey_id = str(uuid.uuid4())

    response = client.post(
        "/surveys/sync",
        headers=headers,
        json={"surveys": [_payload_item(survey_id, zone_id, household_id=household_id)]},
    )
    try:
        assert response.status_code == 200
        body = response.json()
        assert body["errors"] == []
        assert len(body["synced"]) == 1
        assert body["synced"][0]["household_id"] == household_id

        updated = client.get(f"/zones/{zone_id}/households", headers=headers).json()["items"]
        hh118 = next(h for h in updated if h["household_id"] == household_id)
        assert hh118["structural_condition"] == "Semi-pucca"
        assert hh118["population_count"] == 6
        assert hh118["data_confidence"] == "field_verified"

        survey_row = admin_db.execute(
            text("select review_status, display_code from surveys where survey_id = :id"), {"id": survey_id}
        ).mappings().one()
        assert survey_row["review_status"] == "unreviewed"
        assert survey_row["display_code"].startswith("SV-")
    finally:
        admin_db.execute(text("delete from surveys where survey_id = :id"), {"id": survey_id})
        admin_db.commit()
        _restore_household(admin_db, household_id, "HH-118")


def test_retried_sync_with_same_survey_id_does_not_duplicate(client, admin_db):
    """The exact risk named in BUILD-PLAN: the first sync succeeds server-
    side but the client never sees the response (connection drop) and
    retries with the identical survey_id + payload."""
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    household_id = _household_id(client, headers, "ZN-01", "HH-104")
    survey_id = str(uuid.uuid4())
    item = _payload_item(survey_id, zone_id, household_id=household_id)

    try:
        first = client.post("/surveys/sync", headers=headers, json={"surveys": [item]})
        assert first.status_code == 200
        assert first.json()["errors"] == []

        second = client.post("/surveys/sync", headers=headers, json={"surveys": [item]})
        assert second.status_code == 200
        assert second.json()["errors"] == []
        assert second.json()["synced"][0]["household_id"] == first.json()["synced"][0]["household_id"]

        count = admin_db.execute(text("select count(*) from surveys where survey_id = :id"), {"id": survey_id}).scalar()
        assert count == 1
    finally:
        admin_db.execute(text("delete from surveys where survey_id = :id"), {"id": survey_id})
        admin_db.commit()
        _restore_household(admin_db, household_id, "HH-104")


def test_retry_does_not_clobber_a_review_that_happened_in_between(client, admin_db):
    """A slow retry arriving after a supervisor already reviewed the first
    copy must not silently reset review_status back to unreviewed."""
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, officer_headers, "ZN-01")
    household_id = _household_id(client, officer_headers, "ZN-01", "HH-107")
    survey_id = str(uuid.uuid4())
    item = _payload_item(survey_id, zone_id, household_id=household_id)

    try:
        client.post("/surveys/sync", headers=officer_headers, json={"surveys": [item]})
        reviewed = client.patch(f"/surveys/{survey_id}/review", headers=sdma_headers, json={"review_status": "approved"})
        assert reviewed.status_code == 200

        retry = client.post("/surveys/sync", headers=officer_headers, json={"surveys": [item]})
        assert retry.status_code == 200
        assert retry.json()["errors"] == []

        status_row = admin_db.execute(
            text("select review_status from surveys where survey_id = :id"), {"id": survey_id}
        ).scalar()
        assert status_row == "approved"
    finally:
        admin_db.execute(text("delete from surveys where survey_id = :id"), {"id": survey_id})
        admin_db.commit()
        _restore_household(admin_db, household_id, "HH-107")


def test_sync_seeds_a_new_household_when_none_given(client, admin_db):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-03")
    survey_id = str(uuid.uuid4())
    item = _payload_item(survey_id, zone_id, household_id=None, geotag={"type": "Point", "coordinates": [93.04, 25.18]})

    response = client.post("/surveys/sync", headers=headers, json={"surveys": [item]})
    try:
        assert response.status_code == 200
        assert response.json()["errors"] == []
        result = response.json()["synced"][0]
        assert result["survey_display_code"].startswith("SV-")

        created = client.get(f"/zones/{zone_id}/households", headers=headers).json()["items"]
        new_household = next(h for h in created if h["household_id"] == result["household_id"])
        assert new_household["display_code"].startswith("HH-")
        assert new_household["structural_condition"] == "Semi-pucca"
        assert new_household["data_confidence"] == "field_verified"
    finally:
        new_id = response.json()["synced"][0]["household_id"]
        admin_db.execute(text("delete from surveys where survey_id = :id"), {"id": survey_id})
        admin_db.execute(text("delete from households where household_id = :id"), {"id": new_id})
        admin_db.commit()


def test_new_household_without_geotag_reports_error_not_500(client):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    survey_id = str(uuid.uuid4())
    item = _payload_item(survey_id, zone_id, household_id=None, geotag=None)

    response = client.post("/surveys/sync", headers=headers, json={"surveys": [item]})
    assert response.status_code == 200
    assert response.json()["synced"] == []
    assert response.json()["errors"][0]["survey_id"] == survey_id


def test_sync_for_zone_outside_officers_assignment_is_reported_as_error_not_500(client):
    """RLS on zones (Backend Schema §7) hides ZN-02 from this officer
    entirely, so seeding a new household there fails at the zone lookup —
    same security property (an officer can't act on a zone outside their
    assignment) as an insert-time RLS violation, just caught earlier. The
    batch must report it per-item, not 500 the whole request."""
    headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn02_id = _zone_id(client, sdma_headers, "ZN-02")  # not assigned to this officer
    survey_id = str(uuid.uuid4())
    item = _payload_item(survey_id, zn02_id, household_id=None, geotag={"type": "Point", "coordinates": [93.10, 25.10]})

    response = client.post("/surveys/sync", headers=headers, json={"surveys": [item]})
    assert response.status_code == 200
    assert response.json()["synced"] == []
    assert len(response.json()["errors"]) == 1


def test_only_sdma_official_can_review_surveys(client, admin_db):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, officer_headers, "ZN-01")
    household_id = _household_id(client, officer_headers, "ZN-01", "HH-112")
    survey_id = str(uuid.uuid4())
    client.post(
        "/surveys/sync", headers=officer_headers, json={"surveys": [_payload_item(survey_id, zone_id, household_id=household_id)]}
    )
    try:
        forbidden = client.patch(f"/surveys/{survey_id}/review", headers=officer_headers, json={"review_status": "approved"})
        assert forbidden.status_code == 403
    finally:
        admin_db.execute(text("delete from surveys where survey_id = :id"), {"id": survey_id})
        admin_db.commit()
        _restore_household(admin_db, household_id, "HH-112")
