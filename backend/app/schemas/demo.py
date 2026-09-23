from pydantic import BaseModel

from .relocation import RelocationRecordOut
from .survey import SurveyOut


class DemoSeedResponse(BaseModel):
    # Always True — services/demo_seed.py resets relocation_records/surveys
    # before every reseed, so this endpoint always (re)creates fresh rows
    # rather than the seed-once-then-no-op behaviour an earlier version had.
    created: bool
    items: list[RelocationRecordOut]
    counts_by_status: dict[str, int]
    surveys_created: bool
    surveys: list[SurveyOut]
