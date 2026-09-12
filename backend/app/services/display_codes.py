from sqlalchemy import select
from sqlalchemy.orm import Session


def next_display_code(db: Session, prefix: str, column) -> str:
    """Next "PREFIX-N" code for a table using CLAUDE.md's display-code
    convention (MV-118, SV-4471, ...). Finds the highest existing numeric
    suffix rather than counting rows, so a deleted record never causes a
    collision."""
    existing = db.scalars(select(column).where(column.like(f"{prefix}-%"))).all()
    highest = 0
    for code in existing:
        try:
            highest = max(highest, int(code.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"{prefix}-{highest + 1}"
