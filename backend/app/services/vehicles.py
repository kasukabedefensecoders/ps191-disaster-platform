from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Vehicle
from ..schemas.vehicle import VehicleOut


def list_vehicles(db: Session, status: str | None) -> list[VehicleOut]:
    query = select(Vehicle).order_by(Vehicle.vehicle_type)
    if status is not None:
        query = query.where(Vehicle.status == status)
    return [VehicleOut.model_validate(v) for v in db.scalars(query).all()]
