from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from asset_registry.domain.cleaning import (
    parse_attributes,
    parse_coordinate,
    parse_date,
    parse_int,
    parse_optional_float,
    tidy_asset_id,
    tidy_asset_type,
    tidy_description,
    tidy_status,
    tidy_surveyor,
)
from asset_registry.domain.constants import (
    ASSET_ID_PATTERN,
    ASSET_STATUSES,
    ASSET_TYPES,
    CONDITION_MAX,
    CONDITION_MIN,
    DECOMMISSIONED_MAX_CONDITION,
    NAME_MAX_LEN,
    NAME_MIN_LEN,
    condition_band,
)

import re

_ASSET_ID_RE = re.compile(ASSET_ID_PATTERN)


@dataclass
class FieldIssue:
    field: str
    reason: str

    def as_text(self) -> str:
        return f"{self.field}: {self.reason}"


@dataclass
class ValidAsset:
    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    elevation_m: float | None
    surveyed_on: date
    surveyor: str
    status: str
    condition_score: int
    attributes: dict[str, Any]
    condition_band: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "surveyed_on": self.surveyed_on.isoformat(),
            "surveyor": self.surveyor,
            "status": self.status,
            "condition_score": self.condition_score,
            "attributes": self.attributes,
            "condition_band": self.condition_band,
        }


@dataclass
class ValidationResult:
    asset: ValidAsset | None = None
    issues: list[FieldIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.asset is not None and not self.issues

    @property
    def reason(self) -> str:
        return "; ".join(issue.as_text() for issue in self.issues)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def validate_record(
    raw: dict[str, Any],
    *,
    existing_ids: set[str] | None = None,
    require_unique: bool = True,
) -> ValidationResult:
    """Clean and validate one inbound record (CSV row or API payload)."""
    issues: list[FieldIssue] = []

    asset_id = tidy_asset_id(raw.get("asset_id"))
    if not asset_id:
        issues.append(FieldIssue("asset_id", "is missing"))
    elif not _ASSET_ID_RE.match(asset_id):
        issues.append(
            FieldIssue(
                "asset_id",
                "must be two capital letters, a hyphen and four digits (for example PL-0142)",
            )
        )
    elif require_unique and existing_ids is not None and asset_id in existing_ids:
        issues.append(FieldIssue("asset_id", "is already in use"))

    name = tidy_description(raw.get("name") or "")
    if not name:
        issues.append(FieldIssue("name", "is missing"))
    elif len(name) < NAME_MIN_LEN or len(name) > NAME_MAX_LEN:
        issues.append(
            FieldIssue(
                "name",
                f"must be between {NAME_MIN_LEN} and {NAME_MAX_LEN} characters after tidying",
            )
        )

    asset_type = tidy_asset_type(raw.get("asset_type"))
    if not asset_type:
        issues.append(FieldIssue("asset_type", "is missing"))
    elif asset_type not in ASSET_TYPES:
        issues.append(
            FieldIssue(
                "asset_type",
                "must be one of: pole, valve, manhole, transformer",
            )
        )

    latitude = parse_coordinate(raw.get("latitude"))
    if latitude is None:
        issues.append(FieldIssue("latitude", "must be a number between -90 and 90"))
    elif latitude < -90 or latitude > 90:
        issues.append(FieldIssue("latitude", "must be a number between -90 and 90"))

    longitude = parse_coordinate(raw.get("longitude"))
    raw_lon = raw.get("longitude")
    lon_blank = raw_lon is None or str(raw_lon).strip() == ""
    if lon_blank or longitude is None:
        issues.append(FieldIssue("longitude", "must be a number between -180 and 180"))
    elif longitude < -180 or longitude > 180:
        issues.append(FieldIssue("longitude", "must be a number between -180 and 180"))

    elevation = parse_optional_float(raw.get("elevation_m"))
    if isinstance(elevation, str):
        issues.append(FieldIssue("elevation_m", "must be a number when provided"))
        elevation_m: float | None = None
    else:
        elevation_m = elevation

    surveyed_on = parse_date(raw.get("surveyed_on"))
    if surveyed_on is None:
        issues.append(FieldIssue("surveyed_on", "must be a valid date in YYYY-MM-DD form"))
    elif isinstance(surveyed_on, str):
        issues.append(FieldIssue("surveyed_on", "must be a valid date in YYYY-MM-DD form"))
        surveyed_on = None
    elif surveyed_on > _today():
        issues.append(FieldIssue("surveyed_on", "must not be later than today"))

    surveyor = tidy_surveyor(raw.get("surveyor") or "")
    if not surveyor:
        issues.append(FieldIssue("surveyor", "is missing"))

    status = tidy_status(raw.get("status"))
    if not status:
        issues.append(FieldIssue("status", "is missing"))
    elif status not in ASSET_STATUSES:
        issues.append(
            FieldIssue("status", "must be one of: active, decommissioned, proposed")
        )

    condition = parse_int(raw.get("condition_score"))
    if condition is None:
        issues.append(FieldIssue("condition_score", "is missing"))
    elif isinstance(condition, str):
        issues.append(FieldIssue("condition_score", "must be a whole number between 0 and 10"))
        condition = None
    elif condition < CONDITION_MIN or condition > CONDITION_MAX:
        issues.append(FieldIssue("condition_score", "must be a whole number between 0 and 10"))

    attributes = parse_attributes(raw.get("attribute_json", raw.get("attributes")))
    if attributes is None:
        issues.append(FieldIssue("attribute_json", "must be valid JSON"))
    elif isinstance(attributes, str):
        issues.append(FieldIssue("attribute_json", "must be valid JSON"))
        attributes = None

    if (
        status == "decommissioned"
        and isinstance(condition, int)
        and condition > DECOMMISSIONED_MAX_CONDITION
    ):
        issues.append(
            FieldIssue(
                "condition_score",
                "a decommissioned asset may not have a condition rating above 2",
            )
        )

    if issues:
        return ValidationResult(issues=issues)

    assert isinstance(latitude, float)
    assert isinstance(longitude, float)
    assert isinstance(surveyed_on, date)
    assert isinstance(condition, int)
    assert isinstance(attributes, dict)

    asset = ValidAsset(
        asset_id=asset_id,
        name=name,
        asset_type=asset_type,
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation_m,
        surveyed_on=surveyed_on,
        surveyor=surveyor,
        status=status,
        condition_score=condition,
        attributes=attributes,
        condition_band=condition_band(condition),
    )
    return ValidationResult(asset=asset)
