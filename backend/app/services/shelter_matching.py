import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Household, Shelter
from ..scoring import match_factors, match_score
from ..schemas.shelter import ShelterMatchOut

# Phase 7 (routing/OSRM, blocked-segment tracking) isn't built yet, so there
# is no real road-routed distance/duration/access-status source. Rather than
# inventing a dependency on a phase that doesn't exist, or asking the caller
# to guess numbers, this computes an honest proxy from real geometry
# (PostGIS great-circle distance) and says so in the response's `note`.
ASSUMED_AVG_SPEED_KMH = 25.0  # rural hill-road planning assumption, not a routed figure
MATCH_NOTE = (
    "distance_km is straight-line (PostGIS ST_DistanceSphere), not road-routed. "
    f"duration_minutes is estimated from distance_km at a fixed {ASSUMED_AVG_SPEED_KMH:.0f} km/h "
    "planning assumption. route_access defaults to 'clear' — blocked-segment tracking is "
    "Phase 7 (routing), not yet built. Replace all three once Phase 7 lands."
)
INELIGIBLE_STATUSES = ("closed", "damaged")


def match_shelters_for_household(
    db: Session, household_id: uuid.UUID, need: int | None
) -> tuple[list[ShelterMatchOut], int] | None:
    """Returns None if the household isn't visible (RLS-hidden or doesn't
    exist, per Backend Schema §7's household_access policy) — the caller
    404s the same way other RLS-scoped detail lookups do."""
    household = db.get(Household, household_id)
    if household is None:
        return None

    effective_need = need if need is not None else household.population_count

    rows = db.execute(
        select(
            Shelter,
            func.ST_AsGeoJSON(Shelter.geom).label("geom_geojson"),
            (func.ST_DistanceSphere(household.geom, Shelter.geom) / 1000.0).label("distance_km"),
        ).where(Shelter.status.notin_(INELIGIBLE_STATUSES))
    ).all()

    matches = []
    for shelter, geom_geojson, distance_km in rows:
        distance_km = float(distance_km)
        duration_minutes = round(distance_km / ASSUMED_AVG_SPEED_KMH * 60, 1)
        route_access = "clear"

        shelter_dict = {
            "max_capacity": shelter.max_capacity,
            "current_occupancy": shelter.current_occupancy,
            "facilities": shelter.facilities or {},
        }
        factors = match_factors(shelter_dict, effective_need, distance_km, duration_minutes, route_access)
        score = match_score(shelter_dict, effective_need, distance_km, duration_minutes, route_access)

        matches.append(
            ShelterMatchOut(
                shelter_id=shelter.shelter_id,
                display_code=shelter.display_code,
                district_id=shelter.district_id,
                name=shelter.name,
                geom=json.loads(geom_geojson),
                max_capacity=shelter.max_capacity,
                current_occupancy=shelter.current_occupancy,
                facilities=shelter.facilities or {},
                status=shelter.status,
                contact_name=shelter.contact_name,
                contact_phone=shelter.contact_phone,
                needs=shelter.needs or [],
                last_updated_at=shelter.last_updated_at,
                created_at=shelter.created_at,
                updated_at=shelter.updated_at,
                distance_km=round(distance_km, 2),
                duration_minutes=duration_minutes,
                route_access=route_access,
                match_score=score,
                match_factors=factors,
            )
        )

    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches, effective_need
