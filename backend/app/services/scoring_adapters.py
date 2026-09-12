from ..models import Household, Zone

# app.scoring's functions (Phase 2) take plain dicts, not ORM rows — these
# adapters are the one place that conversion happens, shared by every
# service that scores a household against a zone (households.py's ranked
# list, relocations.py's decision endpoint), so the Decimal->float handling
# for zones' Numeric columns only needs getting right once.


def zone_scoring_dict(zone: Zone) -> dict:
    return {
        "risk_score_72h": float(zone.risk_score_72h) if zone.risk_score_72h is not None else 0.0,
        "susceptibility_score": float(zone.susceptibility_score) if zone.susceptibility_score is not None else 0.0,
        "incident_history": zone.incident_history or [],
    }


def household_scoring_dict(household: Household) -> dict:
    return {
        "population_count": household.population_count,
        "children_count": household.children_count,
        "elderly_count": household.elderly_count,
        "assistance_needs_count": household.assistance_needs_count,
        "structural_condition": household.structural_condition,
        "data_confidence": household.data_confidence,
    }
