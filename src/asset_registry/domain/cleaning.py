from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from asset_registry.domain.constants import ASSET_TYPES, ASSET_STATUSES

_WHITESPACE = re.compile(r"\s+")
_COORD = re.compile(
    r"^\s*([NnSsEeWw])?\s*([+-]?\d+(?:\.\d+)?)\s*([NnSsEeWw])?\s*$"
)


def collapse_spaces(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


def tidy_description(value: str) -> str:
    """Trim, collapse repeated spaces, apply consistent capitalisation."""
    return collapse_spaces(str(value)).title()


def tidy_surveyor(value: str) -> str:
    """Standardise a surveyor name so variants of the same person match."""
    return collapse_spaces(str(value)).title()


def tidy_asset_id(value: Any) -> str:
    if value is None:
        return ""
    return collapse_spaces(str(value)).upper()


def tidy_asset_type(value: Any) -> str:
    if value is None:
        return ""
    return collapse_spaces(str(value)).lower()


def tidy_status(value: Any) -> str:
    if value is None:
        return ""
    return collapse_spaces(str(value)).lower()


def parse_coordinate(value: Any) -> float | None:
    """
    Convert a handheld coordinate to a signed decimal degrees value.

    Accepts plain numbers and values with a compass letter such as '28.6148 N'.
    South and west readings become negative.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None

    match = _COORD.match(text)
    if not match:
        return None

    prefix, number, suffix = match.groups()
    magnitude = float(number)
    letter = (prefix or suffix or "").upper()
    if letter in {"S", "W"}:
        return -abs(magnitude)
    if letter in {"N", "E"}:
        return abs(magnitude)
    return magnitude


def parse_optional_float(value: Any) -> float | None | str:
    """
    Parse an optional numeric field.

    Returns None when blank (not recorded). Returns the original text when the
    value is present but not numeric, so validation can reject it.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return text


def parse_int(value: Any) -> int | None | str:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        as_float = float(text)
        as_int = int(as_float)
        if as_float != as_int:
            return text
        return as_int
    except (TypeError, ValueError):
        return text


def parse_date(value: Any) -> date | None | str:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return text


def parse_attributes(value: Any) -> dict[str, Any] | None | str:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if text == "":
        return None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text
    if not isinstance(parsed, dict):
        return text
    return parsed


def is_recognised_type(asset_type: str) -> bool:
    return asset_type in ASSET_TYPES


def is_recognised_status(status: str) -> bool:
    return status in ASSET_STATUSES
