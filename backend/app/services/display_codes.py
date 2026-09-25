from sqlalchemy import text
from sqlalchemy.orm import Session

# Prefix -> sequence name, migration 0008. Kept as an explicit map rather
# than lower-casing the prefix at call time, so a typo'd prefix fails loudly
# (KeyError) instead of silently querying a sequence that happens not to
# exist yet under some other naming rule.
_SEQUENCES = {
    "SV": "display_code_seq_sv",
    "HH": "display_code_seq_hh",
    "HO": "display_code_seq_ho",
    "MV": "display_code_seq_mv",
    "RT": "display_code_seq_rt",
}


def next_display_code(db: Session, prefix: str) -> str:
    """Next "PREFIX-N" code for a table using CLAUDE.md's display-code
    convention (MV-118, SV-4471, ...), via a real Postgres sequence
    (migration 0008) rather than scanning existing rows for the current max.

    That scan used to run through the caller's own request-scoped `db`
    session — the same session RLS applies to — so a field_officer's
    restricted view of surveys/households silently undercounted the true
    max and collided with a real code in a zone outside their assignment.
    A sequence is a schema object, not subject to RLS, and nextval() is
    atomic regardless of concurrent callers or uncommitted rows in the same
    transaction, so it doesn't have either failure mode. See migration
    0008's own docstring for the live bug this replaced.
    """
    sequence = _SEQUENCES[prefix]
    next_value = db.scalar(text(f"select nextval('{sequence}')"))
    return f"{prefix}-{next_value}"
