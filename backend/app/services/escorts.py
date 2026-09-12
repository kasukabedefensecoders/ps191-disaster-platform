from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Escort
from ..schemas.vehicle import EscortOut


def list_escorts(db: Session, status: str | None) -> list[EscortOut]:
    query = select(Escort).order_by(Escort.full_name)
    if status is not None:
        query = query.where(Escort.status == status)
    return [EscortOut.model_validate(e) for e in db.scalars(query).all()]
