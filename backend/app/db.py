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
    """Bind app.current_role/app.current_user_id for this session/connection.

    Uses set_config(..., false) — the "is_local" argument false makes this
    session-scoped (SET, not SET LOCAL), so it survives a commit. Phase 1
    originally used true (transaction-local) and it looked right in
    isolation, but Phase 3 surfaced the real bug: any request that commits
    more than once (e.g. create a zone, then re-read it to build the
    response) silently lost the role context after the first commit ended
    that transaction — the second query ran with no app.current_role set at
    all, so RLS's bypass-for-sdma_official clause evaluated false and the
    row the request had *just inserted* became invisible to it. Safe to
    scope to the whole session/connection here because every RLS-sensitive
    request calls this unconditionally before its first protected query, so
    a pooled connection never runs a query against households/zones/surveys
    on stale context left over from a previous request.

    Passed as bound parameters, not interpolated into SQL text, since these
    are the values the RLS policies on households/zones/surveys read back.
    """
    db.execute(text("select set_config('app.current_role', :role, false)"), {"role": role})
    db.execute(text("select set_config('app.current_user_id', :user_id, false)"), {"user_id": user_id})
