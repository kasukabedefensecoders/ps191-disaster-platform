from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
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
