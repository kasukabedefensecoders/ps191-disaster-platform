import uuid

from pydantic import BaseModel


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: str
    district_id: uuid.UUID | None = None

    class Config:
        from_attributes = True
