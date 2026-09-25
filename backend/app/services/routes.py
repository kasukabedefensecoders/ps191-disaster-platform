import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Route
from ..schemas.route import BlockedSegmentCreate, RouteCreate, RouteOut

# routes carries no RLS (Backend Schema §7 covers households/zones/surveys/
# relocation_records only) — route geometry and blockage status aren't
# household-linked sensitive data, so every authenticated role reads the
# same list, matching shelters/vehicles/escorts.


def _route_select():
    return select(
        Route,
        func.ST_AsGeoJSON(Route.origin_geom).label("origin_geojson"),
        func.ST_AsGeoJSON(Route.dest_geom).label("dest_geojson"),
        func.ST_AsGeoJSON(Route.path).label("path_geojson"),
    )


def _to_route_out(route: Route, origin_geojson: str, dest_geojson: str, path_geojson: str) -> RouteOut:
    return RouteOut(
        route_id=route.route_id,
        display_code=route.display_code,
        origin_geom=json.loads(origin_geojson),
        dest_geom=json.loads(dest_geojson),
        path=json.loads(path_geojson),
        blocked_segments=route.blocked_segments or [],
        distance_km=float(route.distance_km) if route.distance_km is not None else None,
        estimated_duration_minutes=route.estimated_duration_minutes,
        created_at=route.created_at,
        updated_at=route.updated_at,
    )


def list_routes(db: Session, limit: int, offset: int) -> tuple[list[RouteOut], int]:
    total = db.scalar(select(func.count()).select_from(Route)) or 0
    rows = db.execute(_route_select().order_by(Route.display_code).limit(limit).offset(offset)).all()
    return [_to_route_out(*row) for row in rows], total


def get_route(db: Session, route_id) -> RouteOut | None:
    row = db.execute(_route_select().where(Route.route_id == route_id)).first()
    return _to_route_out(*row) if row else None


def _next_route_code(db: Session) -> str:
    from .display_codes import next_display_code

    return next_display_code(db, "RT")


def create_route(db: Session, payload: RouteCreate) -> RouteOut:
    route = Route(
        display_code=_next_route_code(db),
        origin_geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(payload.origin_geom)), 4326),
        dest_geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(payload.dest_geom)), 4326),
        path=func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(payload.path)), 4326),
        distance_km=payload.distance_km,
        estimated_duration_minutes=payload.estimated_duration_minutes,
    )
    db.add(route)
    db.commit()
    return get_route(db, route.route_id)


def add_blocked_segment(db: Session, route_id, payload: BlockedSegmentCreate, reported_by: str) -> RouteOut | None:
    route = db.get(Route, route_id)
    if route is None:
        return None

    segments = list(route.blocked_segments or [])
    segments.append(
        {
            "osm_way_id": payload.osm_way_id,
            "reason": payload.reason,
            "source": payload.source,
            "reported_by": reported_by,
            "reported_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    route.blocked_segments = segments
    db.commit()
    return get_route(db, route_id)


def clear_blocked_segments(db: Session, route_id) -> RouteOut | None:
    route = db.get(Route, route_id)
    if route is None:
        return None
    route.blocked_segments = []
    db.commit()
    return get_route(db, route_id)
