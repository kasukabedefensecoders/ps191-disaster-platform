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


def test_field_officer_cannot_run_or_list_for_unassigned_zone(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn02_id = _zone_id(client, sdma_headers, "ZN-02")

    # 403 (role) fires before the zone lookup, so this confirms RLS
    # separately via the list endpoint (no role gate) instead.
    assert client.get(f"/zones/{zn02_id}/change-detections", headers=officer_headers).status_code == 404
