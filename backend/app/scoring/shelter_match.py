"""Shelter-match scoring.

Ported from PROTOTYPE/PS191 Platform.dc.html's matchFactors()/matchScore().
distance_km/duration_minutes/route_access are function parameters, not
shelter columns — in the prototype they were static demo properties of each
shelter, but in this system they're what the Routing Service (Phase 7, not
built yet) would compute per household/zone. Keeping them as parameters
means this stays a pure function today and doesn't invent a fake dependency
on a phase that doesn't exist yet.
"""
from .factors import build_factor

# The prototype's 4 fixed facility categories ("s.fac", divided by 4 in
# "Facility match") — see docs/BACKEND-SCHEMA.md §6.3.
CANONICAL_FACILITIES = ("water", "medical", "toilets", "power")


def facility_count(facilities: dict) -> int:
    return sum(1 for key in CANONICAL_FACILITIES if facilities.get(key))


def match_factors(shelter: dict, need: int, distance_km: float, duration_minutes: float, route_access: str) -> list[dict]:
    max_capacity = shelter["max_capacity"]
    current_occupancy = shelter["current_occupancy"]
    head = max_capacity - current_occupancy
    fac_count = facility_count(shelter.get("facilities") or {})
    occupancy_pct = round(current_occupancy / max_capacity * 100, 1)

    rows = [
        ("Remaining capacity", 30, head, min(1.0, (head / max(need, 1)) / 3)),
        ("Travel distance", 25, distance_km, max(0.0, 1 - distance_km / 16)),
        ("Facility match", 22, fac_count, fac_count / 4),
        ("Route accessibility", 15, route_access, 1.0 if route_access == "clear" else 0.3),
        ("Occupancy pressure", 8, occupancy_pct, 1 - current_occupancy / max_capacity),
    ]
    return [build_factor(name, weight_pct, input_value, fraction) for name, weight_pct, input_value, fraction in rows]


def match_score(shelter: dict, need: int, distance_km: float, duration_minutes: float, route_access: str) -> float:
    factors = match_factors(shelter, need, distance_km, duration_minutes, route_access)
    return round(sum(f["contribution"] for f in factors), 4)
