from .conftest import login


def _auth_headers(client, email):
    tokens = login(client, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_dashboard_summary_requires_auth(client):
    assert client.get("/dashboard/summary").status_code == 401


def test_sdma_official_sees_full_summary(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    response = client.get("/dashboard/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["zones"]["count"] == 4
    assert body["shelters"]["count"] == 5
    assert body["routes"]["count"] == 4
    assert len(body["top_priority_households"]) <= 10
    assert len(body["top_priority_households"]) > 0

    # rule 1: every score in the summary still carries its factors
    top = body["top_priority_households"][0]
    assert "priority_factors" in top and len(top["priority_factors"]) == 5
    assert "vulnerability_factors" in top and len(top["vulnerability_factors"]) == 5

    # descending priority order across the whole district
    scores = [h["priority_score"] for h in body["top_priority_households"]]
    assert scores == sorted(scores, reverse=True)
    # HH-203 is the highest hand-verified priority_score across all 11
    # seeded households (test_scoring.py's EXPECTED table: 0.83) — ZN-02's
    # GSI-derived risk baseline (0.75, the highest of the four zones) keeps
    # HH-203 on top through both risk_score_72h seed-data revisions; see
    # test_scoring.py's module docstring for what changed and why.
    assert top["display_code"] == "HH-203"
    assert scores[0] == 0.83


def test_field_officer_sees_only_their_zones_in_summary(client):
    headers = _auth_headers(client, "field.officer@ps191.dev")
    response = client.get("/dashboard/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["zones"]["count"] == 2
    zone_codes = {z["display_code"] for z in body["zones"]["items"]}
    assert zone_codes == {"ZN-01", "ZN-03"}

    # every top household must belong to one of the officer's assigned zones
    visible_zone_ids = {z["zone_id"] for z in body["zones"]["items"]}
    assert all(h["zone_id"] in visible_zone_ids for h in body["top_priority_households"])


def test_since_filters_zones_shelters_relocations_but_not_top_households(client):
    headers = _auth_headers(client, "sdma.official@ps191.dev")
    future = client.get("/dashboard/summary", headers=headers, params={"since": "2999-01-01T00:00:00Z"}).json()

    assert future["zones"]["count"] == 0
    assert future["shelters"]["count"] == 0
    assert future["relocations"]["count"] == 0
    # top_priority_households is always live-computed, not since-filtered
    assert len(future["top_priority_households"]) > 0
