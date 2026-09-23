from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, get_scoped_db, require_role
from ..models import User
from ..schemas.demo import DemoSeedResponse
from ..services.demo_seed import seed_demo_relocations

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed-relocations", response_model=DemoSeedResponse)
def seed_relocations(
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
    _: object = Depends(require_role("sdma_official")),
):
    """Rule 6 (sample data stays labelled as sample data): this only ever
    creates relocation_records over the seed's own sample households/
    shelters, and is a no-op once any relocation record exists — see
    services/demo_seed.py."""
    return seed_demo_relocations(db, actor_id=current_user.user_id)
