"""Household priority scoring.

Ported from PROTOTYPE/PS191 Platform.dc.html's prioFactors()/prioScore()/
prioTier(). z.risk and z.susp are already 0-1 in this port (zones.risk_score_72h
and zones.susceptibility_score, per docs/BACKEND-SCHEMA.md), so unlike the
prototype's own `z.risk / 100` this doesn't divide them again — see
docs/BUILD-PLAN.md §1.2 on the score-range decision. prio_tier's thresholds
are the prototype's 68/48 rescaled to 0.68/0.48, and its tier names are the
schema's `immediate`/`short_term`/`medium_term` per §1.1, not the
prototype's `short`/`medium` shorthand.
"""
from .factors import build_factor
from .vulnerability import vuln_score

DATA_CONFIDENCE_UNCERTAINTY = {
    "field_verified": 0.35,
    "baseline": 1.0,
    # Stale verification is treated the same as never-verified (full
    # uncertainty margin) per CLAUDE.md rule 4. The prototype only ever
    # modeled two states (field vs. census); this is the natural extension
    # of the same precautionary-margin rule to the schema's third state.
    "due_for_reverification": 1.0,
}


def prio_factors(household: dict, zone: dict) -> list[dict]:
    risk = zone["risk_score_72h"] or 0.0
    susceptibility = zone["susceptibility_score"] or 0.0
    incident_count = len(zone.get("incident_history") or [])
    confidence = household["data_confidence"]
    uncertainty = DATA_CONFIDENCE_UNCERTAINTY[confidence]
    v_score = vuln_score(household)

    rows = [
        ("72-hour hazard risk", 32, risk, risk),
        ("Household vulnerability", 28, v_score, v_score),
        ("ML susceptibility baseline", 18, susceptibility, susceptibility),
        ("Recorded incident history", 14, incident_count, min(1.0, incident_count / 3)),
        ("Data uncertainty margin", 8, confidence, uncertainty),
    ]
    return [build_factor(name, weight_pct, input_value, fraction) for name, weight_pct, input_value, fraction in rows]


def prio_score(household: dict, zone: dict) -> float:
    return round(sum(f["contribution"] for f in prio_factors(household, zone)), 4)


def prio_tier(score: float) -> str:
    if score >= 0.68:
        return "immediate"
    if score >= 0.48:
        return "short_term"
    return "medium_term"
