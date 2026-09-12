from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_role_context(db: Session, role: str, user_id: str) -> None:
    """Bind app.current_role/app.current_user_id to the current transaction.

    Uses set_config(..., true) rather than `SET LOCAL app.x = <value>` so role
    and user_id are passed as bound parameters, not interpolated into SQL text
    the RLS policies on households/zones/surveys read these back from.
    """
    db.execute(text("select set_config('app.current_role', :role, true)"), {"role": role})
    db.execute(text("select set_config('app.current_user_id', :user_id, true)"), {"user_id": user_id})
