import uuid

from sqlalchemy.orm import Session

from ..models import AuditLog

# The generic audit write path, per docs/BUILD-PLAN.md Phase 6: "every
# relocation decision and every priority-ranking write needs an audit row;
# build the helper here rather than bolting it onto each service
# separately later." Every writer adds the row to the SAME session/
# transaction as the write it's auditing (via db.add, not its own commit)
# so the two either both land or both roll back together — call db.commit()
# once, after this. audit_log is append-only by grant (Backend Schema §7.15
# / migration 0002: app_user has no UPDATE/DELETE on it), so this is the
# only way application code ever touches the table.


def write_audit_log(
    db: Session,
    actor_id: uuid.UUID,
    action_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    factors_snapshot: dict | list | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            factors_snapshot=factors_snapshot,
        )
    )
