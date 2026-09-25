from sqlalchemy import text

from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_list_routes_requires_auth(client):
    assert client.get("/routes").status_code == 401


def test_field_officer_sees_seeded_route_no_rls(client):
    """One route per zone (migration 0012) — RT-07 (real OSM geometry, ZN-01)
    plus a straight-line route to the nearest shelter for each of the other
    three zones, no longer just the single unscoped RT-07 every zone used
    to show identically."""
    headers = _auth_headers(client, "field.officer@ps191.dev")
    response = client.get("/routes", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4

    # zones are RLS-scoped per role (field.officer only sees ZN-01/ZN-03) —
    # routes aren't, so the zone lookup needs the full-visibility role.
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zones = {z["display_code"]: z["zone_id"] for z in client.get("/zones", headers=sdma_headers, params={"limit": 200}).json()["items"]}
    by_code = {r["display_code"]: r for r in body["items"]}
    assert set(by_code) == {"RT-07", "RT-02", "RT-03", "RT-04"}

    rt07 = by_code["RT-07"]
    assert rt07["zone_id"] == zones["ZN-01"]
    assert rt07["path"]["type"] == "LineString"
    assert len(rt07["path"]["coordinates"]) > 40  # real OSM geometry, not a 2-point straight line
    assert rt07["distance_km"] == 12.8
    assert rt07["blocked_segments"] == []

    # each zone's own route has a distinct distance and a straight 2-point
    # path (no OSM stretch was ever fetched for these three areas)
    distances = set()
    for code, zone_code in (("RT-02", "ZN-02"), ("RT-03", "ZN-03"), ("RT-04", "ZN-04")):
        route = by_code[code]
        assert route["zone_id"] == zones[zone_code]
        assert len(route["path"]["coordinates"]) == 2
        assert route["distance_km"] is not None
        distances.add(route["distance_km"])
    assert len(distances) == 3  # genuinely different routes, not the same one 3 times


def test_only_sdma_official_can_create_routes(client, admin_db):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    zone_id = client.get("/zones", headers=sdma_headers, params={"limit": 1}).json()["items"][0]["zone_id"]

    payload = {
        "zone_id": zone_id,
        "origin_geom": {"type": "Point", "coordinates": [93.0, 25.1]},
        "dest_geom": {"type": "Point", "coordinates": [93.05, 25.15]},
        "path": {"type": "LineString", "coordinates": [[93.0, 25.1], [93.05, 25.15]]},
    }
    forbidden = client.post("/routes", headers=officer_headers, json=payload)
    assert forbidden.status_code == 403

    created = client.post("/routes", headers=sdma_headers, json=payload)
    try:
        assert created.status_code == 201
        assert created.json()["display_code"].startswith("RT-")
        assert created.json()["display_code"] != "RT-07"  # a new code, not colliding with the seeded route
    finally:
        admin_db.execute(text("delete from routes where route_id = :id"), {"id": created.json()["route_id"]})
        admin_db.commit()


def test_any_authenticated_role_can_report_a_blocked_segment(client):
    """TRD §7.7: a field officer spotting a landslide-blocked road should be
    able to flag it directly, not need sdma_official to do it for them."""
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    routes = client.get("/routes", headers=officer_headers).json()["items"]
    route_id = routes[0]["route_id"]

    report = client.post(
        f"/routes/{route_id}/blocked-segments",
        headers=officer_headers,
        json={"reason": "landslide debris", "source": "field_report"},
    )
    assert report.status_code == 200
    body = report.json()
    assert len(body["blocked_segments"]) == 1
    assert body["blocked_segments"][0]["reason"] == "landslide debris"
    assert body["blocked_segments"][0]["source"] == "field_report"
    assert "reported_at" in body["blocked_segments"][0]

    sdma_headers = _auth_headers(client, "sdma.official@ps191.dev")
    cleared = client.delete(f"/routes/{route_id}/blocked-segments", headers=sdma_headers)
    assert cleared.status_code == 200
    assert cleared.json()["blocked_segments"] == []


def test_clear_blocked_segments_requires_sdma_official(client):
    officer_headers = _auth_headers(client, "field.officer@ps191.dev")
    routes = client.get("/routes", headers=officer_headers).json()["items"]
    route_id = routes[0]["route_id"]
    response = client.delete(f"/routes/{route_id}/blocked-segments", headers=officer_headers)
    assert response.status_code == 403
