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
from .models import District, Household, Shelter, User, UserZoneAssignment, Zone

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

# code, name, max_capacity, current_occupancy, facilities
# facilities' 4 canonical booleans (water/medical/toilets/power) are the same
# 4 categories matchFactors()'s "Facility match" factor divides by; "other"
# is for anything beyond those 4 (see docs/BACKEND-SCHEMA.md §6.3).
SHELTERS = [
    ("SH-01", "Ridge Higher Secondary School", 450, 180, {"water": True, "medical": True, "toilets": True, "power": True}),
    ("SH-02", "Block Community Hall", 200, 95, {"water": True, "toilets": True}),
    ("SH-03", "District Stadium Ground", 800, 120, {"water": True, "toilets": True, "power": True}),
    ("SH-04", "Block Office Complex", 150, 148, {"water": True, "medical": True, "toilets": True}),
    ("SH-05", "Tea Estate Godown", 300, 0, {"water": True}),
]

# zone_code -> incident_history rows (docs/BACKEND-SCHEMA.md §6.2 shape),
# ported from the prototype's per-zone `incidents` arrays. prio_factors()'s
# "Recorded incident history" factor reads len(incident_history), so this
# has to be populated for the Phase 2 scoring port to reproduce the
# prototype's own priority scores, not just its vulnerability scores.
ZONE_INCIDENTS = {
    "ZN-01": [
        {"hazard_type": "landslide", "date": "2022-05-14", "severity": "high", "source": "GSI historical incident report", "description": "Cluster landslide · 3 casualties, 11 houses lost"},
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


def _point(lon: float, lat: float) -> str:
    return f"SRID=4326;POINT({lon} {lat})"


def _polygon_around(lon: float, lat: float, delta: float = 0.01) -> str:
    return (
        f"SRID=4326;POLYGON(({lon - delta} {lat - delta}, {lon + delta} {lat - delta}, "
        f"{lon + delta} {lat + delta}, {lon - delta} {lat + delta}, {lon - delta} {lat - delta}))"
    )


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

        for code, name, max_capacity, current_occupancy, facilities in SHELTERS:
            shelter = Shelter(
                shelter_id=uuid.uuid4(),
                display_code=code,
                district_id=district.district_id,
                name=name,
                geom=_point(93.35, 25.16),
                max_capacity=max_capacity,
                current_occupancy=current_occupancy,
                facilities=facilities,
            )
            db.add(shelter)
        db.flush()

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
        print(f"Seeded district {district.name}, {len(ZONES)} zones, {len(HOUSEHOLDS)} households, "
              f"{len(SHELTERS)} shelters, {len(SEED_USERS)} users (password: {SEED_PASSWORD}).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
