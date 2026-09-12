import uuid
from datetime import datetime

from pydantic import BaseModel


class VehicleOut(BaseModel):
    vehicle_id: uuid.UUID
    district_id: uuid.UUID
    vehicle_type: str
    capacity: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EscortOut(BaseModel):
    escort_id: uuid.UUID
    user_id: uuid.UUID | None
    full_name: str
    agency: str | None
    contact_phone: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
