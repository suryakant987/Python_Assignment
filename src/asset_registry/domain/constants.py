from __future__ import annotations

ASSET_ID_PATTERN = r"^[A-Z]{2}-\d{4}$"

ASSET_TYPES = frozenset({"pole", "valve", "manhole", "transformer"})
ASSET_STATUSES = frozenset({"active", "decommissioned", "proposed"})

EXPECTED_COLUMNS = (
    "asset_id",
    "name",
    "asset_type",
    "latitude",
    "longitude",
    "elevation_m",
    "surveyed_on",
    "surveyor",
    "status",
    "condition_score",
    "attribute_json",
)

NAME_MIN_LEN = 3
NAME_MAX_LEN = 120
CONDITION_MIN = 0
CONDITION_MAX = 10
DECOMMISSIONED_MAX_CONDITION = 2

DEFAULT_PAGE_LIMIT = 25
MAX_PAGE_LIMIT = 100

ROLE_ADMIN = "admin"
ROLE_SURVEYOR = "surveyor"
VALID_ROLES = frozenset({ROLE_ADMIN, ROLE_SURVEYOR})


def condition_band(score: int) -> str:
    if 8 <= score <= 10:
        return "GOOD"
    if 5 <= score <= 7:
        return "FAIR"
    if 3 <= score <= 4:
        return "POOR"
    return "CRITICAL"
