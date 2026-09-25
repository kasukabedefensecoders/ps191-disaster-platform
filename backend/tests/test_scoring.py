"""Phase 2 — verifies the Python scoring port reproduces the prototype's
own numbers exactly, per docs/BUILD-PLAN.md §1.2's testing requirement
("hand-check HH-112's vulnerability score and factor contributions match
after rescaling, not just the final tier"). Every expected value below was
independently hand-computed from PROTOTYPE/PS191 Platform.dc.html's
vulnFactors()/prioFactors() arithmetic (including its exact per-factor
Math.round-then-sum order) against app.seed's ZONES/HOUSEHOLDS fixtures,
not derived from running this code — that's the point of the check.

Priority expectations were recomputed twice after app.seed's ZONES
risk_score_72h values (vuln expectations are untouched — vuln_score has no
zone dependency):

1. From the prototype's own 6-hour-peak values (0.88/0.81/0.76/0.54) to
   ml/forecast_model.py's actual 72-hour training-curve output
   (0.41/0.48/0.36/0.31) — a real mislabeling fix, found by hand-verifying
   the forecast model in Docker.
2. From that model-exact value to a GSI-derived demo baseline
   (0.72/0.75/0.50/0.52) — reported live: every zone's 72h point is the low
   end of a rain-triggered risk curve that peaks early and recedes by 72h
   (the prototype's own agreed curve shape), so seeding the map's default
   risk badge from it made a GSI-"High" zone display green/low-risk before
   anyone touched the forecast feature. See app/seed.py's own comment on
   ZONES for the full reasoning; the GSI columns themselves are unchanged.

Since risk_score_72h is prio_score's highest-weighted factor (32%), each
revision shifted several of these 11 households' tiers.
"""
import pytest

from app.scoring import (
    facility_count,
    match_score,
    prio_factors,
    prio_score,
    prio_tier,
    vuln_factors,
    vuln_score,
)
from app.seed import HOUSEHOLDS, ZONE_INCIDENTS, ZONES


def _zone_dict(zone_code: str) -> dict:
    for code, _name, _block, _hazards, _population, susp, _gsi_class, _gsi_pct, risk_72h, _confidence, _days_ago in ZONES:
        if code == zone_code:
            return {
                "susceptibility_score": susp,
                "risk_score_72h": risk_72h,
                "incident_history": ZONE_INCIDENTS.get(zone_code, []),
            }
    raise KeyError(zone_code)


def _household_dict(household_code: str) -> tuple[dict, str]:
    for code, zone_code, pop, children, elderly, assist, structure, confidence, _days_ago in HOUSEHOLDS:
        if code == household_code:
            household = {
                "population_count": pop,
                "children_count": children,
                "elderly_count": elderly,
                "assistance_needs_count": assist,
                "structural_condition": structure,
                "data_confidence": confidence,
            }
            return household, zone_code
    raise KeyError(household_code)


# household code -> (vuln_score, prio_score, prio_tier), hand-computed from
# the prototype's own arithmetic (see module docstring).
EXPECTED = {
    "HH-112": (0.9, 0.81, "immediate"),
    "HH-104": (0.65, 0.74, "immediate"),
    "HH-107": (0.43, 0.68, "immediate"),
    "HH-118": (0.1, 0.59, "short_term"),
    "HH-203": (0.8, 0.83, "immediate"),
    "HH-211": (0.35, 0.71, "immediate"),
    "HH-219": (0.38, 0.72, "immediate"),
    "HH-305": (0.73, 0.64, "short_term"),
    "HH-309": (0.29, 0.52, "short_term"),
    "HH-402": (0.31, 0.54, "short_term"),
    "HH-408": (0.6, 0.57, "short_term"),
}


@pytest.mark.parametrize("code", EXPECTED.keys())
def test_household_scores_match_hand_computed_prototype_values(code):
    expected_vuln, expected_prio, expected_tier = EXPECTED[code]
    household, zone_code = _household_dict(code)
    zone = _zone_dict(zone_code)

    assert vuln_score(household) == pytest.approx(expected_vuln, abs=1e-9)

    score = prio_score(household, zone)
    assert score == pytest.approx(expected_prio, abs=1e-9)
    assert prio_tier(score) == expected_tier


def test_half_up_rounding_matches_js_not_python_banker_rounding():
    """HH-107's 'Children under 12' factor is exactly 18 * (1/4) = 4.5 — an
    exact tie. JS's Math.round takes .5 up (5); Python's round() takes it to
    the nearest even number (4). Pinning this case directly, not just via
    the aggregate score, so a regression here fails loudly."""
    household, _ = _household_dict("HH-107")
    children_factor = next(f for f in vuln_factors(household) if f["name"] == "Children under 12")
    assert children_factor["contribution"] == pytest.approx(0.05)


def test_vuln_factors_sum_to_score_and_weights_sum_to_one():
    household, _ = _household_dict("HH-112")
    factors = vuln_factors(household)
    assert sum(f["weight"] for f in factors) == pytest.approx(1.0)
    assert sum(f["contribution"] for f in factors) == pytest.approx(vuln_score(household))


def test_factor_shape_matches_backend_schema_contract():
    household, zone_code = _household_dict("HH-112")
    zone = _zone_dict(zone_code)
    for factor in vuln_factors(household) + prio_factors(household, zone):
        assert set(factor.keys()) == {"name", "weight", "input_value", "contribution"}


def test_baseline_scores_higher_than_field_verified_all_else_equal():
    """CLAUDE.md rule 4: unverified/baseline-only households score higher
    (more urgent) than field-verified ones, all else equal — a
    precautionary margin, intentional, not a bug to "fix"."""
    field_verified = {
        "population_count": 5, "children_count": 1, "elderly_count": 1,
        "assistance_needs_count": 0, "structural_condition": "Semi-pucca",
        "data_confidence": "field_verified",
    }
    baseline = dict(field_verified, data_confidence="baseline")
    due_for_reverification = dict(field_verified, data_confidence="due_for_reverification")
    zone = {"susceptibility_score": 0.7, "risk_score_72h": 0.7, "incident_history": []}

    assert prio_score(baseline, zone) > prio_score(field_verified, zone)
    assert prio_score(due_for_reverification, zone) > prio_score(field_verified, zone)


def test_facility_count_counts_only_the_four_canonical_types():
    assert facility_count({"water": True, "medical": True, "toilets": True, "power": True}) == 4
    assert facility_count({"water": True, "toilets": True}) == 2
    assert facility_count({"water": True, "other": ["generator", "kitchen"]}) == 1


def test_shelter_match_hh112_sh01():
    """HH-112 -> SH-01 is the prototype's own seeded relocation move (MV-118,
    tier 'immediate', pax 9), using SH-01's demo route figures (km:4.2,
    min:18, access:'clear')."""
    shelter = {
        "max_capacity": 450,
        "current_occupancy": 180,
        "facilities": {"water": True, "medical": True, "toilets": True, "power": True},
    }
    score = match_score(shelter, need=9, distance_km=4.2, duration_minutes=18, route_access="clear")
    assert score == pytest.approx(0.90, abs=1e-9)
