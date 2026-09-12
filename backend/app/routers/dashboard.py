from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db
from ..schemas.dashboard import DashboardSummary
from ..services.dashboard import build_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(since: datetime | None = None, db: Session = Depends(get_scoped_db)):
    """Rule 8: since-based delta responses, gzip (global middleware in
    main.py already covers this — assume a satellite-backed link, not
    broadband). Every constituent list is already RLS-scoped the same way
    its own endpoint is, so a field_officer's dashboard is naturally
    limited to their assigned zones without this endpoint doing any of its
    own access-control work."""
    return build_dashboard_summary(db, since)
