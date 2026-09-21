from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TextIO

from sqlalchemy.orm import Session

from asset_registry.db.models import Asset
from asset_registry.domain.constants import EXPECTED_COLUMNS
from asset_registry.domain.validation import validate_record
from asset_registry.services.assets import persist_new_asset, persist_visit_and_update
from asset_registry.services.cache import summary_cache


class MissingColumnsError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            "The file is missing required column(s): " + ", ".join(missing)
        )


class StrictIngestAborted(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class IngestResult:
    rows_read: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    rejects: list[dict[str, Any]] = field(default_factory=list)
    accepted: list[Any] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""


def _normalise_header(name: str) -> str:
    return name.strip().lower()


def confirm_columns(fieldnames: Iterable[str] | None) -> None:
    present = {_normalise_header(name) for name in (fieldnames or []) if name}
    missing = [column for column in EXPECTED_COLUMNS if column not in present]
    if missing:
        raise MissingColumnsError(missing)


def _row_as_original(row: dict[str, Any]) -> dict[str, Any]:
    original: dict[str, Any] = {}
    for column in EXPECTED_COLUMNS:
        original[column] = row.get(column, "")
    return original


def ingest_rows(
    db: Session,
    rows: Iterable[dict[str, Any]],
    *,
    fieldnames: Iterable[str] | None,
    strict: bool = False,
    source: str = "",
) -> IngestResult:
    confirm_columns(fieldnames)
    result = IngestResult(source=source)
    seen_in_file: set[str] = set()

    for raw in rows:
        result.rows_read += 1
        original = _row_as_original({(k.strip().lower() if k else k): v for k, v in raw.items()})
        # Uniqueness: reject a second copy in this file. A code already stored from
        # an earlier survey is a repeat visit, not a reject.
        file_ids = set(seen_in_file)
        validation = validate_record(original, existing_ids=file_ids, require_unique=True)
        if not validation.ok:
            reason = validation.reason
            if strict:
                db.rollback()
                raise StrictIngestAborted(reason)
            rejected = dict(original)
            rejected["reason"] = reason
            result.rejects.append(rejected)
            result.rows_rejected += 1
            continue

        asset = validation.asset
        assert asset is not None
        seen_in_file.add(asset.asset_id)
        stored = db.query(Asset).filter(Asset.asset_id == asset.asset_id).one_or_none()
        if stored is None:
            persist_new_asset(db, asset)
        else:
            persist_visit_and_update(db, stored, asset)
        result.accepted.append(asset)
        result.rows_accepted += 1

    db.commit()
    summary_cache.invalidate()
    return result


def ingest_csv_file(
    db: Session,
    csv_path: Path,
    *,
    strict: bool = False,
) -> IngestResult:
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return ingest_csv_handle(db, handle, strict=strict, source=str(path))


def ingest_csv_handle(
    db: Session,
    handle: TextIO,
    *,
    strict: bool = False,
    source: str = "upload",
) -> IngestResult:
    reader = csv.DictReader(handle)
    return ingest_rows(
        db,
        reader,
        fieldnames=reader.fieldnames,
        strict=strict,
        source=source,
    )
