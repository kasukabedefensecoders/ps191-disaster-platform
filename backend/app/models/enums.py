from sqlalchemy.dialects.postgresql import ENUM

USER_ROLE = ENUM(
    "sdma_official", "field_officer", "control_room",
    name="user_role", create_type=False,
)

HAZARD_TYPE = ENUM(
    "flood", "landslide", "cloudburst", "coastal_erosion",
    name="hazard_type", create_type=False,
)

DATA_CONFIDENCE = ENUM(
    "baseline", "field_verified", "due_for_reverification",
    name="data_confidence", create_type=False,
)

STRUCTURAL_CONDITION = ENUM(
    "Kutcha", "Semi-pucca", "Pucca", "unknown",
    name="structural_condition", create_type=False,
)

PRIORITY_TIER = ENUM(
    "immediate", "short_term", "medium_term",
    name="priority_tier", create_type=False,
)

SHELTER_STATUS = ENUM(
    "active", "full", "closed", "damaged",
    name="shelter_status", create_type=False,
)

REVIEW_STATUS = ENUM(
    "unreviewed", "approved", "flagged",
    name="review_status", create_type=False,
)

RELOCATION_STATUS = ENUM(
    "assigned", "in_transit", "arrived",
    name="relocation_status", create_type=False,
)

VEHICLE_STATUS = ENUM(
    "available", "assigned", "in_transit", "unavailable",
    name="vehicle_status", create_type=False,
)

HANDOFF_STATUS = ENUM(
    "open", "acknowledged", "in_progress", "resolved",
    name="handoff_status", create_type=False,
)
