from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db
from ..schemas.vehicle import VehicleOut
from ..services.vehicles import list_vehicles

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def get_vehicles(status: str | None = Query(default=None), db: Session = Depends(get_scoped_db)):
    """No RLS on vehicles (Backend Schema §7) — used to pick an available
    vehicle when creating a relocation record (?status=available)."""
    return list_vehicles(db, status)
