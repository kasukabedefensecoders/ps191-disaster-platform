from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db
from ..schemas.vehicle import EscortOut
from ..services.escorts import list_escorts

router = APIRouter(prefix="/escorts", tags=["escorts"])


@router.get("", response_model=list[EscortOut])
def get_escorts(status: str | None = Query(default=None), db: Session = Depends(get_scoped_db)):
    """No RLS on escorts (Backend Schema §7) — used to pick an available
    escort when creating a relocation record (?status=available)."""
    return list_escorts(db, status)
