from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Shelter, User
from ..schemas.shelter import ShelterAccessToken, ShelterLoginRequest
from .dependencies import get_current_user
from .schemas import AccessToken, RefreshRequest, TokenPair, UserOut
from .security import create_access_token, create_refresh_token, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form_data.username))
    if user is None or not user.is_active or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="incorrect email or password")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenPair(
        access_token=create_access_token(str(user.user_id), user.role),
        refresh_token=create_refresh_token(str(user.user_id), user.role),
    )


@router.post("/refresh", response_model=AccessToken)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise invalid

    if payload.get("type") != "refresh":
        raise invalid

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise invalid

    return AccessToken(access_token=create_access_token(str(user.user_id), user.role))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/shelter-login", response_model=ShelterAccessToken)
def shelter_login(body: ShelterLoginRequest, db: Session = Depends(get_db)):
    """A shelter officer authenticates with just the shelter's own display
    code (SH-01, ...) — no separate account or password, per the shelter
    officer dashboard's code-based login. This is deliberately a much
    lighter credential than the sdma_official/field_officer/control_room
    login: shelters already carry no RLS and no household-level PII, and
    the resulting token only ever unlocks GET/PATCH /shelters/me for that
    one shelter (see get_current_shelter), never the full shelters list or
    any other endpoint."""
    code = body.shelter_code.strip()
    shelter = db.scalar(select(Shelter).where(func.upper(Shelter.display_code) == code.upper()))
    if shelter is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid shelter code")

    return ShelterAccessToken(
        access_token=create_access_token(str(shelter.shelter_id), "shelter_officer"),
        shelter_id=shelter.shelter_id,
        display_code=shelter.display_code,
        name=shelter.name,
    )
