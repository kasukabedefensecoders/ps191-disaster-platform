"""Seed the dev database with the prototype's Dima Hasao demo data.

Ported verbatim from PROTOTYPE/PS191 Platform.dc.html's ZONES/households/
shelters arrays (same IDs, same values) so the Phase 2 scoring port can be
checked against the prototype's own numbers. Run with:

    python -m app.seed
"""
import math
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
#
# risk_72h below is a GSI-derived demo baseline (gsi_score/100 plus a small
# offset), not ml/forecast_model.py's raw 72-hour training-curve output for
# these zones (0.41/0.48/0.36/0.31). A previous revision of this seed used
# that model-exact value — correct in the narrow sense of matching what
# predict_with_factors() returns at horizon=72, and verified as such by
# hand in Docker — but it created a real, reported problem: every one of
# this district's zones has a rain-triggered risk curve that PEAKS early
# (6-24h) and RECEDES by 72h (see ml/forecast_model.py's
# TRAINING_TARGETS_PCT — the prototype's own agreed curve shape, not
# something invented here), so the model's 72h point is *always* the low
# end of the curve. Seeding the map's default/pre-"Generate" risk badge
# from that specific point meant a zone GSI marks "High" displayed
# green/low-risk on first load — confusing on its own, and specifically
# reported as looking broken right after "Reset demo data", since that's
# the demo's fresh-state default. Fixed by decoupling the two: the GSI
# classification/score columns are unchanged (still the real, static,
# dataset-sourced classification — TRD §8.1), but the *seeded* risk_72h
# is now chosen to land in the same colour band as gsi_classification on
# the map (riskColor.ts: >=65 red/orange for "High", 45-64 amber for
# "Moderate") rather than to equal any one specific point on the model's
# own trained curve. Clicking "Generate forecast" still calls the real
# model and can legitimately show a different, lower number afterward —
# that's the model's genuine output and is left alone; only the *default,
# nobody's-touched-it-yet* baseline is curated for GSI-consistency here.
ZONES = [
    ("ZN-01", "Upper Ridge", "Haflong block · ward 4", ["landslide"], 412, 0.91, "High", 70, 0.72, "field_verified", 4),
    ("ZN-02", "Riverbend East", "Maibang block · ward 2", ["flood"], 1240, 0.84, "High", 72, 0.75, "baseline", None),
    ("ZN-03", "Slate Quarry", "Haflong block · ward 6", ["landslide", "cloudburst"], 268, 0.88, "Moderate", 45, 0.50, "field_verified", 12),
    ("ZN-04", "Mill Colony", "Maibang block · ward 5", ["flood"], 890, 0.62, "Moderate", 48, 0.52, "due_for_reverification", 96),
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
    # code, name, max_capacity, current_occupancy, facilities, (lon, lat), status, contact_name, contact_phone, needs
    # contact_phone uses the +91 90000 0000X block — an all-zeros prefix
    # with a bare 1-5 suffix reads as unambiguously fake to anyone, unlike
    # the +91 98765 43210 block this replaced: that one is the common
    # "placeholder number" convention in Indian software demos, but it's
    # still a real, dialable-looking number, which is exactly the risk this
    # avoids. (94350 11201-style numbers were dropped earlier for the same
    # reason — that prefix is a real, currently-allocated operator block.)
    ("SH-01", "Ridge Higher Secondary School", 450, 180, {"water": True, "medical": True, "toilets": True, "power": True}, (93.0205, 25.1700), "active", "D. Langthasa", "+91 90000 00001", []),
    ("SH-02", "Block Community Hall", 200, 95, {"water": True, "toilets": True}, (93.1255, 25.3035), "active", "P. Jeme", "+91 90000 00002", []),
    ("SH-03", "District Stadium Ground", 800, 120, {"water": True, "toilets": True, "power": True}, (93.0115, 25.1620), "active", "S. Hojai", "+91 90000 00003", []),
    ("SH-04", "Block Office Complex", 150, 148, {"water": True, "medical": True, "toilets": True}, (92.7020, 25.4650), "active", "R. Thaosen", "+91 90000 00004", ["food", "blankets"]),
    # SH-05: PROTOTYPE/PS191 Platform.dc.html's own seed marks this shelter
    # "Standby" (0 occupancy, held in reserve) — ported as the schema's new
    # standby status rather than "active" with zero occupants.
    ("SH-05", "Tea Estate Godown", 300, 0, {"water": True}, (92.9580, 25.0320), "standby", "N. Barman", "+91 90000 00005", []),
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

# display_code, vehicle_type, capacity, route_label — the 2 trucks are
# ported from the prototype's move MV-118 example ("Truck AS-04 · cap 24");
# the 5 buses are new (Logistics Tracker's bus-consolidation cards, migration
# 0005) so several households can ride the same vehicle to the same shelter.
# Road transport only, deliberately: this platform is pre-disaster predictive
# relocation (moving people out ahead of a forecast hazard, not rescuing them
# mid-flood), so the seeded fleet assumes the road network is still intact —
# no boats/amphibious vehicles here even for the flood zones (ZN-02/ZN-04).
VEHICLES = [
    ("VH-01", "Truck", 24, None),
    ("VH-02", "Truck", 18, None),
    ("BUS-01", "Bus", 50, "Ridge Route"),
    ("BUS-02", "Bus", 50, "Maibang Route"),
    ("BUS-03", "Bus", 50, "Stadium Route"),
    ("BUS-04", "Bus", 50, "Ridge Route B"),
    ("BUS-05", "Bus", 50, "Maibang Route B"),
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
ASSUMED_AVG_SPEED_KMH = 25.0  # same rural hill-road planning assumption as shelter_matching.py
RT07_DURATION_MINUTES = round(RT07_DISTANCE_KM / ASSUMED_AVG_SPEED_KMH * 60)

# RT-07 is real OSM road geometry, but it's the only route this system ever
# seeded — every zone but ZN-01 (RT-07's own zone: the prototype's own
# "Route RT-07 · Upper Ridge -> SH-01" label, Upper Ridge being ZN-01)
# had no evacuation route of its own at all, so the Evacuation Routes
# screen showed the same RT-07 regardless of which zone a judge was
# looking at. ZN-02/03/04 get their own route here to the nearest eligible
# shelter, computed the same honest way services/shelter_matching.py
# already handles "no OSRM instance": straight-line great-circle distance,
# duration from ASSUMED_AVG_SPEED_KMH — not disguised as road-routed
# geometry the way RT-07 genuinely is.


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nearest_shelter(zone_lon: float, zone_lat: float) -> tuple[str, float, float, float]:
    """(shelter_code, shelter_lon, shelter_lat, distance_km) for whichever
    seeded shelter is straight-line closest to a zone's centroid."""
    best: tuple[str, float, float, float] | None = None
    for code, _name, _cap, _occ, _fac, (slon, slat), *_rest in SHELTERS:
        dist = _haversine_km(zone_lon, zone_lat, slon, slat)
        if best is None or dist < best[3]:
            best = (code, slon, slat, dist)
    assert best is not None
    return best


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

        shelters_by_code: dict[str, Shelter] = {}
        for code, name, max_capacity, current_occupancy, facilities, (lon, lat), status, contact_name, contact_phone, needs in SHELTERS:
            shelter = Shelter(
                shelter_id=uuid.uuid4(),
                display_code=code,
                district_id=district.district_id,
                name=name,
                geom=_point(lon, lat),
                max_capacity=max_capacity,
                current_occupancy=current_occupancy,
                facilities=facilities,
                status=status,
                contact_name=contact_name,
                contact_phone=contact_phone,
                needs=needs,
            )
            db.add(shelter)
            shelters_by_code[code] = shelter
        db.flush()

        for display_code, vehicle_type, capacity, route_label in VEHICLES:
            db.add(
                Vehicle(
                    vehicle_id=uuid.uuid4(),
                    district_id=district.district_id,
                    display_code=display_code,
                    route_label=route_label,
                    vehicle_type=vehicle_type,
                    capacity=capacity,
                )
            )

        for full_name, agency in ESCORTS:
            db.add(Escort(escort_id=uuid.uuid4(), full_name=full_name, agency=agency))

        origin_lon, origin_lat = RT07_PATH_COORDS[0]
        dest_lon, dest_lat = RT07_PATH_COORDS[-1]
        db.add(
            Route(
                route_id=uuid.uuid4(),
                display_code="RT-07",
                zone_id=zones_by_code["ZN-01"].zone_id,
                shelter_id=shelters_by_code["SH-01"].shelter_id,
                origin_geom=_point(origin_lon, origin_lat),
                dest_geom=_point(dest_lon, dest_lat),
                path=_linestring(RT07_PATH_COORDS),
                distance_km=RT07_DISTANCE_KM,
                estimated_duration_minutes=RT07_DURATION_MINUTES,
            )
        )

        for i, zone_code in enumerate(("ZN-02", "ZN-03", "ZN-04"), start=2):
            zone_lon, zone_lat = ZONE_CENTROIDS[zone_code]
            shelter_code, shelter_lon, shelter_lat, distance_km = _nearest_shelter(zone_lon, zone_lat)
            duration_minutes = round(distance_km / ASSUMED_AVG_SPEED_KMH * 60)
            db.add(
                Route(
                    route_id=uuid.uuid4(),
                    display_code=f"RT-0{i}",
                    zone_id=zones_by_code[zone_code].zone_id,
                    shelter_id=shelters_by_code[shelter_code].shelter_id,
                    origin_geom=_point(zone_lon, zone_lat),
                    dest_geom=_point(shelter_lon, shelter_lat),
                    path=_linestring([(zone_lon, zone_lat), (shelter_lon, shelter_lat)]),
                    distance_km=round(distance_km, 2),
                    estimated_duration_minutes=duration_minutes,
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

        # Phase 11's curated before/after pairs, one per zone (migration
        # 0010: stored in Postgres, not MinIO — no MinIO instance exists on
        # the live deployment). Runs after the transaction commits rather
        # than inside it, each call managing its own short-lived session.
        for zone_code in zones_by_code:
            ensure_sample_imagery_for_zone(zone_code)

        print(f"Seeded district {district.name}, {len(ZONES)} zones, {len(HOUSEHOLDS)} households, "
              f"{len(SHELTERS)} shelters, {len(VEHICLES)} vehicles, {len(ESCORTS)} escorts, {len(ZONES)} routes, "
              f"{len(SEED_USERS)} users (password: {SEED_PASSWORD}), sample imagery for all {len(ZONES)} zones.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
