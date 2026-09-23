from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..db import get_db, set_role_context
from ..models import Shelter, User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except ValueError:
        raise credentials_error

    if payload.get("type") != "access":
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


def get_scoped_db(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Session:
    """The same request-scoped session, with app.current_role/current_user_id
    bound to the transaction so RLS on households/zones/surveys applies."""
    set_role_context(db, current_user.role, str(current_user.user_id))
    return db


def get_current_shelter(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Shelter:
    """Shelter-officer sessions (POST /auth/shelter-login) are a deliberately
    separate, lower-trust credential from get_current_user's — a shelter
    officer isn't a row in `users`, doesn't get a users.user_id `sub`, and
    doesn't go through set_role_context/RLS at all. The JWT's `sub` is the
    shelter_id itself and `role` is the fixed string "shelter_officer",
    scoping the session to exactly one shelter by construction rather than
    by a role check a route could forget to add. See docs/TRD.md §10."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate shelter credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except ValueError:
        raise credentials_error

    if payload.get("type") != "access" or payload.get("role") != "shelter_officer":
        raise credentials_error

    shelter_id = payload.get("sub")
    if shelter_id is None:
        raise credentials_error

    shelter = db.get(Shelter, shelter_id)
    if shelter is None:
        raise credentials_error

    return shelter


def require_role(*roles: str):
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return current_user

    return _check
