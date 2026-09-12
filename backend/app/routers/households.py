import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth.dependencies import get_scoped_db
from ..schemas.shelter import ShelterMatchListResponse
from ..services.shelter_matching import MATCH_NOTE, match_shelters_for_household

router = APIRouter(prefix="/households", tags=["households"])


@router.get("/{household_id}/shelter-matches", response_model=ShelterMatchListResponse)
def list_shelter_matches(
    household_id: uuid.UUID,
    need: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_scoped_db),
):
    """Phase 5 (docs/BUILD-PLAN.md): wires matchFactors()/matchScore() into
    a real endpoint — ranked best-match first, for one household against
    every eligible shelter (closed/damaged excluded). RLS on `households`
    scopes this the same way as everything else: a field_officer can only
    match shelters for a household in one of their assigned zones. `need`
    defaults to the household's full population_count when omitted."""
    result = match_shelters_for_household(db, household_id, need)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="household not found")
    matches, effective_need = result
    return ShelterMatchListResponse(items=matches, count=len(matches), need=effective_need, note=MATCH_NOTE)
