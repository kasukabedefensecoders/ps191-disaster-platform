"""Phase 11: differencing/thresholding change detection against the one
curated (synthetic) before/after pair seeded for ZN-01 (see
app/cv/change_detection.py's module docstring for what's real vs.
labeled-synthetic).
"""
from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _zone_id(client, headers, display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    return next(z["zone_id"] for z in zones if z["display_code"] == display_code)


def test_run_requires_auth(client):
    zone_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/zones/{zone_id}/change-detections/run").status_code == 401


def test_only_sdma_official_can_run_detection(client):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    assert client.post(f"/zones/{zone_id}/change-detections/run", headers=headers).status_code == 403


def test_run_detection_on_curated_pair_finds_the_simulated_scar(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")

    response = client.post(f"/zones/{zone_id}/change-detections/run", headers=headers)
    try:
        assert response.status_code == 200
        body = response.json()
        assert body["before_image_ref"] == "zones/ZN-01/before.png"
        assert body["after_image_ref"] == "zones/ZN-01/after.png"
        assert body["affected_area_geom"]["type"] == "MultiPolygon"
        assert len(body["affected_area_geom"]["coordinates"]) >= 1
        # the simulated scar covers roughly (60/200)*(60/200) ~ 9% of the
        # 200x200 frame — well above noise-level Otsu thresholding on flat
        # terrain, well below "the whole image changed"
        assert 0.02 < body["confidence"] < 0.5

        listed = client.get(f"/zones/{zone_id}/change-detections", headers=headers).json()
        assert body["detection_id"] in {d["detection_id"] for d in listed["items"]}
    finally:
        admin_db.execute(text("delete from change_detections where detection_id = :id"), {"id": response.json()["detection_id"]})
        admin_db.commit()


def test_run_detection_without_curated_imagery_returns_400(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-02")  # no imagery seeded for this zone
    response = client.post(f"/zones/{zone_id}/change-detections/run", headers=headers)
    assert response.status_code == 400


def test_run_detection_cross_references_households_and_surveys_in_the_scar(client, admin_db):
    """PRD §7.11 / TRD §8.3: the affected-area polygon must be cross-
    referenced against households/surveys ("who is affected", not just
    "where"). Places one household and one survey point inside the
    synthetic scar's known lon/lat footprint (see
    app/cv/change_detection.py's ORIGIN/PIXEL_SIZE_DEG and the
    after[70:130, 55:125] patch) and confirms both come back on the
    detection row; a household sitting well outside the scar is confirmed
    absent."""
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")

    inside_household_id = "11111111-1111-1111-1111-111111111111"
    inside_survey_id = "22222222-2222-2222-2222-222222222222"
    outside_household_id = "33333333-3333-3333-3333-333333333333"
    admin_db.execute(
        text(
            "insert into households (household_id, display_code, zone_id, geom, population_count, "
            "structural_condition, data_confidence) values "
            "(:id, 'HH-TEST-IN', :zone_id, ST_SetSRID(ST_MakePoint(93.014, 25.165), 4326), 3, 'Kutcha', 'baseline')"
        ),
        {"id": inside_household_id, "zone_id": str(zone_id)},
    )
    admin_db.execute(
        text(
            "insert into households (household_id, display_code, zone_id, geom, population_count, "
            "structural_condition, data_confidence) values "
            "(:id, 'HH-TEST-OUT', :zone_id, ST_SetSRID(ST_MakePoint(93.02, 25.16), 4326), 3, 'Kutcha', 'baseline')"
        ),
        {"id": outside_household_id, "zone_id": str(zone_id)},
    )
    admin_db.execute(
        text(
            "insert into surveys (survey_id, zone_id, household_id, officer_id, submitted_at, payload, geotag, review_status) "
            "values (:id, :zone_id, :household_id, "
            "(select user_id from users where email = 'field.officer@ps191.dev'), "
            "now(), '{}'::jsonb, ST_SetSRID(ST_MakePoint(93.0145, 25.1645), 4326), 'unreviewed')"
        ),
        {"id": inside_survey_id, "zone_id": str(zone_id), "household_id": inside_household_id},
    )
    admin_db.commit()

    response = client.post(f"/zones/{zone_id}/change-detections/run", headers=headers)
    try:
        assert response.status_code == 200
        body = response.json()
        assert inside_household_id in body["cross_referenced_household_ids"]
        assert outside_household_id not in body["cross_referenced_household_ids"]
        assert inside_survey_id in body["cross_referenced_survey_ids"]
    finally:
        admin_db.execute(text("delete from change_detections where detection_id = :id"), {"id": response.json()["detection_id"]})
        admin_db.execute(text("delete from surveys where survey_id = :id"), {"id": inside_survey_id})
        admin_db.execute(
            text("delete from households where household_id in (:in_id, :out_id)"),
            {"in_id": inside_household_id, "out_id": outside_household_id},
        )
        admin_db.commit()


def test_zone_image_endpoint_serves_real_png_bytes(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")

    before = client.get(f"/zones/{zone_id}/change-detections/image/before", headers=headers)
    after = client.get(f"/zones/{zone_id}/change-detections/image/after", headers=headers)
    assert before.status_code == 200
    assert after.status_code == 200
    assert before.headers["content-type"] == "image/png"
    assert before.content[:8] == b"\x89PNG\r\n\x1a\n"  # real PNG magic bytes, not a placeholder string
    assert before.content != after.content  # a genuine before/after pair, not the same file twice


def test_zone_image_404s_for_zone_without_curated_imagery(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-02")
    assert client.get(f"/zones/{zone_id}/change-detections/image/before", headers=headers).status_code == 404


def test_zone_image_requires_auth(client):
    zone_id = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/zones/{zone_id}/change-detections/image/before").status_code == 401


def test_field_officer_cannot_run_or_list_for_unassigned_zone(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn02_id = _zone_id(client, sdma_headers, "ZN-02")

    # 403 (role) fires before the zone lookup, so this confirms RLS
    # separately via the list endpoint (no role gate) instead.
    assert client.get(f"/zones/{zn02_id}/change-detections", headers=officer_headers).status_code == 404
