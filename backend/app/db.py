from sqlalchemy import create_engine, event, text
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


def _apply_role_context(connection, role: str, user_id: str) -> None:
    connection.execute(text("select set_config('app.current_role', :role, false)"), {"role": role})
    connection.execute(text("select set_config('app.current_user_id', :user_id, false)"), {"user_id": user_id})


def set_role_context(db: Session, role: str, user_id: str) -> None:
    """Bind app.current_role/app.current_user_id for every transaction this
    session runs, not just its current one.

    Phase 1 used set_config(..., true) (SET LOCAL — transaction-scoped) and
    Phase 3 found the bug that caused: a request that commits more than
    once (create a zone, then re-read it to build the response) lost the
    role context the instant the first commit ended that transaction, so
    the second query ran with no app.current_role set and the row the
    request had *just inserted* became invisible under RLS. The Phase 3
    fix switched to set_config(..., false) (session-scoped SET, survives a
    commit) reasoning that "every RLS-sensitive request calls this
    unconditionally before its first protected query" — true, but it
    assumed the request's Session keeps using the same physical connection
    for its whole lifetime. It doesn't: a commit() releases the connection
    back to the pool, and the Session's next statement can be handed a
    *different* pooled connection that never had these GUCs set at all
    (pool_size > 1 in app/config.py's default engine settings) — same
    symptom Phase 3 diagnosed (RLS evaluates as if app.current_user_id is
    unset), just one commit later than before. Real and reproducible: any
    write path that commits more than once per request — Change 2/3's
    relocation create-then-status-advance-to-arrived, or the demo-seed
    endpoint looping over several create_relocation calls — could 500 on
    an empty app.current_user_id cast to uuid.

    The actual fix has to outlive any single connection: `db.info` is
    carried on the Session object itself across every transaction it opens
    (commits included), and the after_begin listener below re-applies
    these two set_config calls to whichever connection backs *each* new
    transaction — the first one and every one after a commit — rather than
    only the connection that happened to be checked out when this function
    was called.

    Passed as bound parameters, not interpolated into SQL text, since these
    are the values the RLS policies on households/zones/surveys/
    relocation_records read back.
    """
    db.info["app_role"] = role
    db.info["app_user_id"] = user_id
    _apply_role_context(db.connection(), role, user_id)


@event.listens_for(Session, "after_begin")
def _reapply_role_context_on_new_transaction(session, transaction, connection) -> None:
    role = session.info.get("app_role")
    user_id = session.info.get("app_user_id")
    if role is not None:
        _apply_role_context(connection, role, user_id)
