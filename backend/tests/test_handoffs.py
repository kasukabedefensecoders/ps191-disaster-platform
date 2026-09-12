from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _zone_id(client, headers, display_code):
    zones = client.get("/zones", headers=headers, params={"limit": 200}).json()["items"]
    return next(z["zone_id"] for z in zones if z["display_code"] == display_code)


def test_list_requires_auth(client):
    assert client.get("/handoffs").status_code == 401


def test_create_requires_at_least_one_context_field(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    response = client.post("/handoffs", headers=headers, json={"need_type": "Medical", "agency": "District Health Services"})
    assert response.status_code == 422


def test_field_officer_can_create_a_handoff_not_gated(client, admin_db):
    """PRD §7.13: a field officer spotting a need should be able to route
    it directly — unlike relocation decisions, this isn't an sdma_official-
    only action."""
    headers = _auth_headers(client, "field.officer@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    payload = {"need_type": "Rescue", "agency": "NDRF 1st Bn · Guwahati", "zone_id": zone_id, "description": "4 residents cut off"}

    response = client.post("/handoffs", headers=headers, json=payload)
    try:
        assert response.status_code == 201
        body = response.json()
        assert body["display_code"].startswith("HO-")
        assert body["status"] == "open"
        assert body["acknowledged_at"] is None
        assert body["resolved_at"] is None
    finally:
        admin_db.execute(text("delete from handoff_logs where log_id = :id"), {"id": response.json()["log_id"]})
        admin_db.commit()


def test_only_sdma_official_can_update_status(client, admin_db):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    created = client.post(
        "/handoffs", headers=headers, json={"need_type": "Transport", "agency": "District Transport Office", "zone_id": zone_id}
    )
    log_id = created.json()["log_id"]

    try:
        forbidden = client.patch(f"/handoffs/{log_id}/status", headers=headers, json={"status": "acknowledged"})
        assert forbidden.status_code == 403

        acknowledged = client.patch(f"/handoffs/{log_id}/status", headers=sdma_headers, json={"status": "acknowledged"})
        assert acknowledged.status_code == 200
        body = acknowledged.json()
        assert body["status"] == "acknowledged"
        first_ack_time = body["acknowledged_at"]
        assert first_ack_time is not None

        # moving on to resolved keeps the original acknowledged_at
        resolved = client.patch(f"/handoffs/{log_id}/status", headers=sdma_headers, json={"status": "resolved"})
        assert resolved.status_code == 200
        assert resolved.json()["acknowledged_at"] == first_ack_time
        assert resolved.json()["resolved_at"] is not None
    finally:
        admin_db.execute(text("delete from handoff_logs where log_id = :id"), {"id": log_id})
        admin_db.commit()


def test_invalid_status_value_rejected(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    created = client.post("/handoffs", headers=headers, json={"need_type": "Medical", "agency": "District Health Services", "zone_id": zone_id})
    log_id = created.json()["log_id"]
    try:
        response = client.patch(f"/handoffs/{log_id}/status", headers=headers, json={"status": "not-a-real-status"})
        assert response.status_code == 422
    finally:
        admin_db.execute(text("delete from handoff_logs where log_id = :id"), {"id": log_id})
        admin_db.commit()


def test_dashboard_summary_includes_handoffs(client, admin_db):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = _zone_id(client, headers, "ZN-01")
    created = client.post("/handoffs", headers=headers, json={"need_type": "Engineering", "agency": "PWD Roads Division", "zone_id": zone_id})
    log_id = created.json()["log_id"]

    try:
        summary = client.get("/dashboard/summary", headers=headers).json()
        assert log_id in {h["log_id"] for h in summary["handoffs"]["items"]}
    finally:
        admin_db.execute(text("delete from handoff_logs where log_id = :id"), {"id": log_id})
        admin_db.commit()
