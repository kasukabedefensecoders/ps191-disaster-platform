import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Household, Zone
from ..scoring import prio_factors, prio_score, prio_tier, vuln_factors, vuln_score
from ..schemas.household import HouseholdRankedOut
from .scoring_adapters import household_scoring_dict, zone_scoring_dict

# households.priority_tier/vulnerability_score exist as columns (Backend
# Schema §5.4) but Phase 2 wasn't wired to write them anywhere, and nothing
# in this system yet triggers a recompute-and-persist cycle (that's a
# survey-ingestion concern — Phase 9 — or a future recompute job, not this
# read endpoint). So this computes fresh on every read rather than trusting
# stale/never-populated columns. A GET must stay side-effect-free, so it
# does not write the result back either.


def _to_ranked_out(household: Household, geom_geojson: str, zone_scoring: dict) -> HouseholdRankedOut:
    household_scoring = household_scoring_dict(household)
    v_factors = vuln_factors(household_scoring)
    v_score = vuln_score(household_scoring)
    p_factors = prio_factors(household_scoring, zone_scoring)
    p_score = prio_score(household_scoring, zone_scoring)

    return HouseholdRankedOut(
        household_id=household.household_id,
        display_code=household.display_code,
        zone_id=household.zone_id,
        geom=json.loads(geom_geojson),
        population_count=household.population_count,
        children_count=household.children_count,
        elderly_count=household.elderly_count,
        assistance_needs_count=household.assistance_needs_count,
        structural_condition=household.structural_condition,
        data_confidence=household.data_confidence,
        last_surveyed_at=household.last_surveyed_at,
        vulnerability_score=v_score,
        vulnerability_factors=v_factors,
        priority_score=p_score,
        priority_tier=prio_tier(p_score),
        priority_factors=p_factors,
    )


def list_zone_households(
    db: Session, zone_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[HouseholdRankedOut], int] | None:
    """Returns None if the zone itself isn't visible (RLS-hidden or doesn't
    exist) — the caller 404s the same way zones.get_zone does, so a
    field_officer's 404 for an unassigned zone doesn't distinguish
    "doesn't exist" from "exists but isn't yours" (Backend Schema §7)."""
    zone = db.get(Zone, zone_id)
    if zone is None:
        return None
    zone_scoring = zone_scoring_dict(zone)

    total = db.scalar(select(func.count()).select_from(Household).where(Household.zone_id == zone_id)) or 0

    rows = db.execute(
        select(Household, func.ST_AsGeoJSON(Household.geom).label("geom_geojson"))
        .where(Household.zone_id == zone_id)
    ).all()

    ranked = sorted(
        (_to_ranked_out(household, geom_geojson, zone_scoring) for household, geom_geojson in rows),
        key=lambda h: h.priority_score,
        reverse=True,
    )
    return ranked[offset : offset + limit], total
