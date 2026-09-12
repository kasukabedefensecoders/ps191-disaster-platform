import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import HandoffLog
from ..schemas.handoff import HandoffLogCreate, HandoffLogOut
from .display_codes import next_display_code

# No RLS on handoff_logs (Backend Schema §7 covers households/zones/
# surveys/relocation_records only) — an interagency need (medical, rescue,
# transport, engineering) isn't the household-linked sensitive data rule 7
# protects, and routing it to the right agency needs every role to see it.


def create_handoff(db: Session, payload: HandoffLogCreate) -> HandoffLogOut:
    handoff = HandoffLog(
        log_id=uuid.uuid4(),
        display_code=next_display_code(db, "HO", HandoffLog.display_code),
        need_type=payload.need_type,
        agency=payload.agency,
        description=payload.description,
        linked_record_id=payload.linked_record_id,
        zone_id=payload.zone_id,
        household_id=payload.household_id,
    )
    db.add(handoff)
    db.commit()
    db.refresh(handoff)
    return HandoffLogOut.model_validate(handoff)


def list_handoffs(db: Session, since: datetime | None, limit: int, offset: int) -> tuple[list[HandoffLogOut], int]:
    query = select(HandoffLog).order_by(HandoffLog.raised_at.desc())
    count_query = select(func.count()).select_from(HandoffLog)
    if since is not None:
        query = query.where(HandoffLog.updated_at > since)
        count_query = count_query.where(HandoffLog.updated_at > since)

    total = db.scalar(count_query) or 0
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return [HandoffLogOut.model_validate(r) for r in rows], total


def get_handoff(db: Session, log_id: uuid.UUID) -> HandoffLogOut | None:
    handoff = db.get(HandoffLog, log_id)
    return HandoffLogOut.model_validate(handoff) if handoff else None


def update_status(db: Session, log_id: uuid.UUID, new_status: str) -> HandoffLogOut | None:
    """Backend Schema doesn't constrain handoff_status transitions the way
    chk_status_timestamps does for relocation_records, so this allows any
    of the 4 values in any order (an agency can go straight from 'open' to
    'resolved', or a resolved need can be reopened) rather than inventing
    a stricter state machine the schema doesn't call for. Each timestamp
    is set the first time its status is reached and never cleared, so the
    history of when a need was first acknowledged/resolved survives even
    if the status later changes again."""
    handoff = db.get(HandoffLog, log_id)
    if handoff is None:
        return None

    handoff.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "acknowledged" and handoff.acknowledged_at is None:
        handoff.acknowledged_at = now
    if new_status == "resolved" and handoff.resolved_at is None:
        handoff.resolved_at = now

    db.commit()
    db.refresh(handoff)
    return HandoffLogOut.model_validate(handoff)
