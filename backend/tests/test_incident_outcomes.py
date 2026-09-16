"""Phase 13 (PRD §7.12 / TRD §8.4): post-incident ground-truth capture.
Checks the sdma_official write gate, RLS-through-zone scoping (the same
pattern forecasts/change-detections use), and the auto-correlation with
the most recent 72h forecast generated before occurred_at.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _zone_id(client, headers, display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    return next(z["zone_id"] for z in zones if z["display_code"] == display_code)


def test_create_requires_auth(client):
    zone_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/zones/{zone_id}/incident-outcomes", json={"occurred_at": "2026-01-01T00:00:00Z"}).status_code == 401


def test_only_sdma_official_can_record_an_outcome(client):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    response = client.post(
        f"/zones/{zone_id}/incident-outcomes", headers=headers, json={"occurred_at": "2026-01-01T00:00:00Z"}
    )
    assert response.status_code == 403


def test_create_auto_links_the_most_recent_forecast_and_lists_it_back(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    original = admin_db.execute(text("select risk_score_72h from zones where zone_id = :id"), {"id": zone_id}).scalar()

    generated = client.post(f"/zones/{zone_id}/forecasts/generate", headers=headers)
    assert generated.status_code == 200
    forecast_72h = next(f for f in generated.json()["forecasts"] if f["horizon_hours"] == 72)

    occurred_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.post(
        f"/zones/{zone_id}/incident-outcomes",
        headers=headers,
        json={
            "occurred_at": occurred_at,
            "shelter_adequate": True,
            "route_held_up": False,
            "notes": "Route RT-07 washed out near km 8; shelter held up fine.",
        },
    )
    try:
        assert response.status_code == 201
        body = response.json()
        assert body["zone_id"] == zone_id
        assert body["shelter_adequate"] is True
        assert body["route_held_up"] is False
        assert body["forecast_id"] == forecast_72h["forecast_id"]
        assert body["predicted_score"] == forecast_72h["score"]
        assert body["predicted_horizon_hours"] == 72

        listed = client.get(f"/zones/{zone_id}/incident-outcomes", headers=headers).json()
        assert body["outcome_id"] in {o["outcome_id"] for o in listed["items"]}
        relisted = next(o for o in listed["items"] if o["outcome_id"] == body["outcome_id"])
        assert relisted["predicted_score"] == forecast_72h["score"]
    finally:
        admin_db.execute(text("delete from incident_outcomes where zone_id = :id"), {"id": zone_id})
        admin_db.execute(text("delete from risk_forecasts where zone_id = :id"), {"id": zone_id})
        admin_db.execute(
            text("update zones set risk_score_72h = :orig, risk_score_factors = null where zone_id = :id"),
            {"orig": original, "id": zone_id},
        )
        admin_db.commit()


def test_field_officer_cannot_list_for_unassigned_zone(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zn02_id = _zone_id(client, sdma_headers, "ZN-02")  # not assigned to this officer
    response = client.get(f"/zones/{zn02_id}/incident-outcomes", headers=officer_headers)
    assert response.status_code == 404
