"""Seed the dev database with the prototype's Dima Hasao demo data.

Ported verbatim from PROTOTYPE/PS191 Platform.dc.html's ZONES/households/
shelters arrays (same IDs, same values) so the Phase 2 scoring port can be
checked against the prototype's own numbers. Run with:

    python -m app.seed
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .auth.security import hash_password
from .db import SessionLocal
from .models import District, Escort, Household, Route, Shelter, User, UserZoneAssignment, Vehicle, Zone
from .services.change_detection import ensure_sample_imagery_for_zone

NOW = datetime.now(timezone.utc)

DISTRICT = {"name": "Dima Hasao", "state": "Assam", "primary_hazards": ["landslide", "flood"]}

# id, name, block, hazards, population, susp, gsi_classification, gsi_score, risk_72h, data_confidence, days_since_verified
ZONES = [
    ("ZN-01", "Upper Ridge", "Haflong block · ward 4", ["landslide"], 412, 0.91, "High", 70, 0.88, "field_verified", 4),
    ("ZN-02", "Riverbend East", "Maibang block · ward 2", ["flood"], 1240, 0.84, "High", 72, 0.81, "baseline", None),
    ("ZN-03", "Slate Quarry", "Haflong block · ward 6", ["landslide", "cloudburst"], 268, 0.88, "Moderate", 45, 0.76, "field_verified", 12),
    ("ZN-04", "Mill Colony", "Maibang block · ward 5", ["flood"], 890, 0.62, "Moderate", 48, 0.54, "due_for_reverification", 96),
]

# code, zone_code, population, children, elderly, assistance, structure, source(->data_confidence), days_since_surveyed
HOUSEHOLDS = [
    ("HH-112", "ZN-01", 9, 4, 1, 2, "Kutcha", "field_verified", 4),
    ("HH-104", "ZN-01", 6, 2, 1, 1, "Kutcha", "field_verified", 4),
    ("HH-107", "ZN-01", 4, 1, 2, 0, "Semi-pucca", "field_verified", 4),
    ("HH-118", "ZN-01", 3, 0, 0, 0, "Pucca", "field_verified", 4),
    ("HH-203", "ZN-02", 7, 3, 2, 1, "Kutcha", "baseline", None),
    ("HH-211", "ZN-02", 5, 1, 1, 0, "Semi-pucca", "baseline", None),
    ("HH-219", "ZN-02", 2, 0, 2, 1, "Pucca", "baseline", None),
    ("HH-305", "ZN-03", 8, 3, 1, 1, "Kutcha", "field_verified", 12),
    ("HH-309", "ZN-03", 4, 2, 0, 0, "Semi-pucca", "field_verified", 12),
    ("HH-402", "ZN-04", 6, 2, 1, 0, "Pucca", "baseline", None),
    ("HH-408", "ZN-04", 5, 2, 2, 1, "Semi-pucca", "field_verified", 96),
]

# code, name, max_capacity, current_occupancy, facilities, (lon, lat)
# facilities' 4 canonical booleans (water/medical/toilets/power) are the same
# 4 categories matchFactors()'s "Facility match" factor divides by; "other"
# is for anything beyond those 4 (see docs/BACKEND-SCHEMA.md §6.3).
# Coordinates are the same ones PROTOTYPE/dima-hasao-map.html already uses
# for these 5 shelters (real, distinct points, not the zone-centroid
# placeholder every shelter shared before Phase 5) — needed for real
# distance to mean anything once shelter_matching.py computes it.
SHELTERS = [
    ("SH-01", "Ridge Higher Secondary School", 450, 180, {"water": True, "medical": True, "toilets": True, "power": True}, (93.0205, 25.1700)),
    ("SH-02", "Block Community Hall", 200, 95, {"water": True, "toilets": True}, (93.1255, 25.3035)),
    ("SH-03", "District Stadium Ground", 800, 120, {"water": True, "toilets": True, "power": True}, (93.0115, 25.1620)),
    ("SH-04", "Block Office Complex", 150, 148, {"water": True, "medical": True, "toilets": True}, (92.7020, 25.4650)),
    ("SH-05", "Tea Estate Godown", 300, 0, {"water": True}, (92.9580, 25.0320)),
]

# zone_code -> incident_history rows (docs/BACKEND-SCHEMA.md §6.2 shape),
# ported from the prototype's per-zone `incidents` arrays. prio_factors()'s
# "Recorded incident history" factor reads len(incident_history), so this
# has to be populated for the Phase 2 scoring port to reproduce the
# prototype's own priority scores, not just its vulnerability scores.
#
# ZN-01's first entry is a real, sourced event (district-wide, not
# zone-specific — see docs/BUILD-PLAN.md's "Phase 3 data-sourcing findings"
# for the citation and the honest limits of what could be verified);
# every other entry below is still representative sample data like the
# rest of this file (rule 6 — never presented as live government data).
ZONE_INCIDENTS = {
    "ZN-01": [
        {"hazard_type": "landslide", "date": "2022-05-11", "severity": "high", "source": "Kumar et al., Landslides (2022) 10.1007/s10346-022-01977-6; AGU Landslide Blog", "description": "Real, verified district-wide event: 5,178 landslides triggered by 156mm rainfall in 24h (540mm for the month); ~57,000 people displaced district-wide, 3 deaths, New Haflong railway station buried by an ~8m-deep debris flow. Haflong block (this zone's real-world area) was within the affected area; attribution to this specific synthetic zone/household count is illustrative, not GSI-sourced."},
        {"hazard_type": "landslide", "date": "2019-07-02", "severity": "moderate", "source": "GSI historical incident report", "description": "Slope failure · road cut for 9 days"},
        {"hazard_type": "landslide", "date": "2016-06-28", "severity": "moderate", "source": "GSI historical incident report", "description": "Debris flow · 2 houses damaged"},
    ],
    "ZN-02": [
        {"hazard_type": "flood", "date": "2024-06-19", "severity": "high", "source": "GSI historical incident report", "description": "Flood · 240 households displaced"},
        {"hazard_type": "flood", "date": "2022-05-16", "severity": "high", "source": "GSI historical incident report", "description": "Flood · embankment breach, 2 wards cut off"},
        {"hazard_type": "flood", "date": "2020-07-11", "severity": "moderate", "source": "GSI historical incident report", "description": "Flood · livestock and crop loss"},
    ],
    "ZN-03": [
        {"hazard_type": "landslide", "date": "2023-08-04", "severity": "moderate", "source": "GSI historical incident report", "description": "Slip above habitation · no casualties"},
        {"hazard_type": "cloudburst", "date": "2021-09-22", "severity": "moderate", "source": "GSI historical incident report", "description": "Cloudburst · flash debris through 4 plots"},
    ],
    "ZN-04": [
        {"hazard_type": "flood", "date": "2022-05-18", "severity": "moderate", "source": "GSI historical incident report", "description": "Flood · 60 households displaced"},
        {"hazard_type": "flood", "date": "2019-07-06", "severity": "low", "source": "GSI historical incident report", "description": "Waterlogging · 4 days"},
    ],
}

SEED_USERS = [
    ("Anjali Rao", "sdma.official@ps191.dev", "sdma_official"),
    ("Kali Thaosen", "field.officer@ps191.dev", "field_officer"),
    ("Ranjit Langthasa", "control.room@ps191.dev", "control_room"),
]
SEED_PASSWORD = "ps191-demo-pass"

# field officer's assigned zones for the RLS test to have something to check
FIELD_OFFICER_ZONES = ["ZN-01", "ZN-03"]

# vehicle_type, capacity — ported from the prototype's move MV-118 example
# ("Truck AS-04 · cap 24"); vehicles/escorts aren't in CLAUDE.md's
# display-code list (only relocation records — "MV-xxx" — are), so these
# are referenced by UUID only, same as the schema defines them.
VEHICLES = [
    ("Truck", 24),
    ("Truck", 18),
]

# full_name, agency — ported from the prototype's "NDRF Sqd 2 · 3 pax"
ESCORTS = [
    ("NDRF Sqd 2", "NDRF 1st Bn · Guwahati"),
    ("NDRF Sqd 4", "NDRF 1st Bn · Guwahati"),
]

# Phase 7 (docs/BUILD-PLAN.md): real OSM road geometry (NH627 near Haflong,
# fetched from the Overpass API on 2026-09-12, downsampled from 776 to ~50
# points), not a synthetic straight line — verifies TRD §13's flagged risk
# ("OSM coverage for a rural, hilly district may be too sparse for sensible
# routes") is not actually a problem for this stretch: 12.8 km of continuous
# trunk-road geometry runs directly past the ZN-01/SH-01/SH-03 area. This is
# real road data with no live OSRM instance behind it yet (that step —
# osrm-extract/partition/contract over a proper .osm.pbf — needs a properly
# resourced environment this session didn't have; see the Phase 7 note in
# the BUILD-PLAN for what was and wasn't verified).
RT07_PATH_COORDS = [
    (93.025157, 25.126496), (93.024677, 25.129017), (93.025002, 25.130252), (93.024518, 25.131424),
    (93.023003, 25.130845), (93.021897, 25.131241), (93.020267, 25.131724), (93.018303, 25.132138),
    (93.017653, 25.133133), (93.018895, 25.134255), (93.018569, 25.135624), (93.018824, 25.136788),
    (93.019853, 25.137460), (93.019317, 25.138633), (93.020432, 25.140499), (93.021849, 25.140589),
    (93.022077, 25.141930), (93.022876, 25.143760), (93.023898, 25.145172), (93.025805, 25.147239),
    (93.025741, 25.148074), (93.025707, 25.149495), (93.025649, 25.150852), (93.025641, 25.152552),
    (93.024543, 25.154253), (93.023029, 25.155389), (93.021442, 25.156033), (93.018960, 25.156632),
    (93.017006, 25.157112), (93.015524, 25.157673), (93.014076, 25.160229), (93.015681, 25.159619),
    (93.017652, 25.159699), (93.017757, 25.163828), (93.018342, 25.166953), (93.017665, 25.168562),
    (93.015450, 25.169823), (93.015584, 25.171609), (93.014875, 25.173544), (93.015936, 25.186022),
    (93.017582, 25.187784), (93.019641, 25.187544), (93.019552, 25.188288), (93.019137, 25.188958),
    (93.020705, 25.188765), (93.021047, 25.190540), (93.021013, 25.193065), (93.021464, 25.194786),
    (93.018421, 25.196728), (93.018101, 25.198565), (93.017938, 25.199816), (93.015590, 25.199611),
    (93.014083, 25.200428),
]
RT07_DISTANCE_KM = 12.8  # real, computed from the full (non-downsampled) geometry
RT07_DURATION_MINUTES = round(RT07_DISTANCE_KM / 25 * 60)  # same 25 km/h planning assumption as Phase 5/6


def _point(lon: float, lat: float) -> str:
    return f"SRID=4326;POINT({lon} {lat})"


def _polygon_around(lon: float, lat: float, delta: float = 0.01) -> str:
    return (
        f"SRID=4326;POLYGON(({lon - delta} {lat - delta}, {lon + delta} {lat - delta}, "
        f"{lon + delta} {lat + delta}, {lon - delta} {lat + delta}, {lon - delta} {lat - delta}))"
    )


def _linestring(coords: list[tuple[float, float]]) -> str:
    pts = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"SRID=4326;LINESTRING({pts})"


# Approximate centroids inside Dima Hasao district, spaced out for the demo map.
ZONE_CENTROIDS = {
    "ZN-01": (93.02, 25.16),
    "ZN-02": (93.10, 25.10),
    "ZN-03": (93.04, 25.18),
    "ZN-04": (93.12, 25.06),
}


def seed() -> None:
    db = SessionLocal()
    try:
        db.execute(text("select set_config('app.current_role', 'sdma_official', true)"))

        district = District(
            district_id=uuid.uuid4(),
            name=DISTRICT["name"],
            state=DISTRICT["state"],
            primary_hazards=DISTRICT["primary_hazards"],
        )
        db.add(district)
        db.flush()

        zones_by_code: dict[str, Zone] = {}
        for code, name, block, hazards, population, susp, gsi_class, gsi_pct, risk_72h, confidence, days_ago in ZONES:
            lon, lat = ZONE_CENTROIDS[code]
            zone = Zone(
                zone_id=uuid.uuid4(),
                display_code=code,
                district_id=district.district_id,
                name=f"{name} ({block})",
                geom=_polygon_around(lon, lat),
                hazard_types=hazards,
                population=population,
                incident_history=ZONE_INCIDENTS.get(code, []),
                data_confidence=confidence,
                last_verified_at=(NOW - timedelta(days=days_ago)) if days_ago is not None else None,
                susceptibility_score=susp,
                gsi_classification=gsi_class,
                gsi_score=gsi_pct,
                risk_score_72h=risk_72h,
                risk_score_updated_at=NOW,
            )
            db.add(zone)
            zones_by_code[code] = zone
        db.flush()

        for code, zone_code, pop, children, elderly, assist, structure, confidence, days_ago in HOUSEHOLDS:
            zone = zones_by_code[zone_code]
            lon, lat = ZONE_CENTROIDS[zone_code]
            household = Household(
                household_id=uuid.uuid4(),
                display_code=code,
                zone_id=zone.zone_id,
                geom=_point(lon, lat),
                population_count=pop,
                children_count=children,
                elderly_count=elderly,
                assistance_needs_count=assist,
                structural_condition=structure,
                data_confidence=confidence,
                last_surveyed_at=(NOW - timedelta(days=days_ago)) if days_ago is not None else None,
            )
            db.add(household)

        for code, name, max_capacity, current_occupancy, facilities, (lon, lat) in SHELTERS:
            shelter = Shelter(
                shelter_id=uuid.uuid4(),
                display_code=code,
                district_id=district.district_id,
                name=name,
                geom=_point(lon, lat),
                max_capacity=max_capacity,
                current_occupancy=current_occupancy,
                facilities=facilities,
            )
            db.add(shelter)
        db.flush()

        for vehicle_type, capacity in VEHICLES:
            db.add(Vehicle(vehicle_id=uuid.uuid4(), district_id=district.district_id, vehicle_type=vehicle_type, capacity=capacity))

        for full_name, agency in ESCORTS:
            db.add(Escort(escort_id=uuid.uuid4(), full_name=full_name, agency=agency))

        origin_lon, origin_lat = RT07_PATH_COORDS[0]
        dest_lon, dest_lat = RT07_PATH_COORDS[-1]
        db.add(
            Route(
                route_id=uuid.uuid4(),
                display_code="RT-07",
                origin_geom=_point(origin_lon, origin_lat),
                dest_geom=_point(dest_lon, dest_lat),
                path=_linestring(RT07_PATH_COORDS),
                distance_km=RT07_DISTANCE_KM,
                estimated_duration_minutes=RT07_DURATION_MINUTES,
            )
        )

        users_by_role: dict[str, User] = {}
        for full_name, email, role in SEED_USERS:
            user = User(
                user_id=uuid.uuid4(),
                full_name=full_name,
                email=email,
                password_hash=hash_password(SEED_PASSWORD),
                role=role,
                district_id=district.district_id,
            )
            db.add(user)
            users_by_role[role] = user
        db.flush()

        field_officer = users_by_role["field_officer"]
        for zone_code in FIELD_OFFICER_ZONES:
            db.add(UserZoneAssignment(user_id=field_officer.user_id, zone_id=zones_by_code[zone_code].zone_id))

        db.commit()

        # Phase 11's one curated before/after pair — MinIO, not the DB, so
        # this runs after the transaction commits rather than inside it.
        ensure_sample_imagery_for_zone("ZN-01")

        print(f"Seeded district {district.name}, {len(ZONES)} zones, {len(HOUSEHOLDS)} households, "
              f"{len(SHELTERS)} shelters, {len(VEHICLES)} vehicles, {len(ESCORTS)} escorts, 1 route, "
              f"{len(SEED_USERS)} users (password: {SEED_PASSWORD}), sample imagery for ZN-01.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
