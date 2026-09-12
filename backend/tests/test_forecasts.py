"""Phase 10: real XGBoost + SHAP forecast pipeline (see
app/ml/forecast_model.py's module docstring for what's real vs. labeled
placeholder). Checks the factors[] shape (rule 1), one row per horizon per
generation cycle (not one row for all six), RLS scoping, and that the
zones.risk_score_72h denormalized cache actually gets refreshed.
"""
from sqlalchemy import text

from .conftest import login

EXPECTED_HORIZONS = {6, 12, 24, 36, 48, 72}


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _zone_id(client, headers, display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    return next(z["zone_id"] for z in zones if z["display_code"] == display_code)


def test_generate_requires_auth(client):
    zone_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/zones/{zone_id}/forecasts/generate").status_code == 401


def test_only_sdma_official_can_generate(client):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    response = client.post(f"/zones/{zone_id}/forecasts/generate", headers=headers)
    assert response.status_code == 403


def test_generate_produces_one_row_per_horizon_with_real_factors(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    original = admin_db.execute(text("select risk_score_72h from zones where zone_id = :id"), {"id": zone_id}).scalar()

    response = client.post(f"/zones/{zone_id}/forecasts/generate", headers=headers)
    try:
        assert response.status_code == 200
        body = response.json()
        forecasts = body["forecasts"]
        assert len(forecasts) == 6
        assert {f["horizon_hours"] for f in forecasts} == EXPECTED_HORIZONS
        assert len({f["generated_at"] for f in forecasts}) == 1  # one generation cycle

        for f in forecasts:
            assert 0.0 <= f["score"] <= 1.0
            assert f["model_version"].startswith("xgb-")
            assert len(f["factors"]) == 4
            for factor in f["factors"]:
                assert set(factor.keys()) == {"name", "weight", "input_value", "contribution"}

        # different horizons for the same zone must not all get identical
        # factors — that would mean horizon_hours isn't actually influencing
        # the model (a real regression bug this exact assertion would catch)
        contributions_by_horizon = {f["horizon_hours"]: tuple(fa["contribution"] for fa in f["factors"]) for f in forecasts}
        assert len(set(contributions_by_horizon.values())) > 1

        zone = client.get(f"/zones/{zone_id}", headers=headers).json()
        seventy_two = next(f for f in forecasts if f["horizon_hours"] == 72)
        assert zone["risk_score_72h"] == seventy_two["score"]
        assert zone["risk_score_factors"] == seventy_two["factors"]
    finally:
        admin_db.execute(text("delete from risk_forecasts where zone_id = :id"), {"id": zone_id})
        admin_db.execute(
            text("update zones set risk_score_72h = :orig, risk_score_factors = null where zone_id = :id"),
            {"orig": original, "id": zone_id},
        )
        admin_db.commit()


def test_list_forecasts_requires_auth(client):
    zone_id = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/zones/{zone_id}/forecasts").status_code == 401


def test_field_officer_cannot_list_forecasts_for_unassigned_zone(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn02_id = _zone_id(client, sdma_headers, "ZN-02")  # not assigned to this officer
    response = client.get(f"/zones/{zn02_id}/forecasts", headers=officer_headers)
    assert response.status_code == 404


def test_generate_for_zone_without_placeholder_features_returns_400(client, admin_db):
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    district_id = client.get("/zones", headers=sdma_headers).json()["items"][0]["district_id"]
    payload = {
        "display_code": "ZN-TEST-FORECAST",
        "district_id": district_id,
        "name": "No Feature Data Zone",
        "geom": {"type": "Polygon", "coordinates": [[[93.0, 25.0], [93.01, 25.0], [93.01, 25.01], [93.0, 25.01], [93.0, 25.0]]]},
        "hazard_types": ["flood"],
    }
    created = client.post("/zones", headers=sdma_headers, json=payload)
    zone_id = created.json()["zone_id"]
    try:
        response = client.post(f"/zones/{zone_id}/forecasts/generate", headers=sdma_headers)
        assert response.status_code == 400
    finally:
        admin_db.execute(text("delete from zones where zone_id = :id"), {"id": zone_id})
        admin_db.commit()
