from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from asset_registry.errors import AppError
from asset_registry.db.models import Asset, Visit
from asset_registry.domain.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, condition_band
from asset_registry.domain.validation import ValidAsset, validate_record
from asset_registry.services.cache import summary_cache


def _existing_ids(db: Session) -> set[str]:
    return set(db.scalars(select(Asset.asset_id)).all())


def to_public(asset: Asset, visit_count: int | None = None) -> dict[str, Any]:
    payload = {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "elevation_m": asset.elevation_m,
        "surveyed_on": asset.surveyed_on.isoformat(),
        "surveyor": asset.surveyor,
        "status": asset.status,
        "condition_score": asset.condition_score,
        "attributes": asset.attributes or {},
        "condition_band": condition_band(asset.condition_score),
    }
    if visit_count is not None:
        payload["visit_count"] = visit_count
    return payload


def _apply_validated(asset: Asset, valid: ValidAsset) -> None:
    asset.asset_id = valid.asset_id
    asset.name = valid.name
    asset.asset_type = valid.asset_type
    asset.latitude = valid.latitude
    asset.longitude = valid.longitude
    asset.elevation_m = valid.elevation_m
    asset.surveyed_on = valid.surveyed_on
    asset.surveyor = valid.surveyor
    asset.status = valid.status
    asset.condition_score = valid.condition_score
    asset.attributes = valid.attributes


def _add_visit(db: Session, asset: Asset, valid: ValidAsset, notes: str | None = None) -> None:
    db.add(
        Visit(
            asset=asset,
            surveyed_on=valid.surveyed_on,
            surveyor=valid.surveyor,
            condition_score=valid.condition_score,
            notes=notes or valid.name,
        )
    )


def persist_new_asset(db: Session, valid: ValidAsset, notes: str | None = None) -> Asset:
    asset = Asset()
    _apply_validated(asset, valid)
    db.add(asset)
    _add_visit(db, asset, valid, notes=notes)
    summary_cache.invalidate()
    return asset


def persist_visit_and_update(db: Session, asset: Asset, valid: ValidAsset) -> Asset:
    _apply_validated(asset, valid)
    _add_visit(db, asset, valid)
    summary_cache.invalidate()
    return asset


def create_asset(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    result = validate_record(payload, existing_ids=_existing_ids(db), require_unique=True)
    if not result.ok:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": i.field, "reason": i.reason} for i in result.issues],
        )
    assert result.asset is not None
    asset = persist_new_asset(db, result.asset)
    db.commit()
    db.refresh(asset)
    return to_public(asset)


def get_asset_or_404(db: Session, asset_id: str) -> Asset:
    asset = db.scalar(
        select(Asset)
        .options(selectinload(Asset.visits))
        .where(Asset.asset_id == asset_id.upper())
    )
    if asset is None:
        raise AppError(
            status_code=404,
            error="not_found",
            message=f"No asset with code {asset_id} exists.",
            details=[{"field": "asset_id", "reason": "does not exist"}],
        )
    return asset


def replace_asset(db: Session, asset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    asset = get_asset_or_404(db, asset_id)
    data = dict(payload)
    data["asset_id"] = asset.asset_id
    result = validate_record(data, existing_ids=None, require_unique=False)
    if not result.ok:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": i.field, "reason": i.reason} for i in result.issues],
        )
    assert result.asset is not None
    persist_visit_and_update(db, asset, result.asset)
    db.commit()
    db.refresh(asset)
    return to_public(asset)


def patch_asset(db: Session, asset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    asset = get_asset_or_404(db, asset_id)
    current = {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "latitude": asset.latitude,
        "longitude": asset.longitude,
        "elevation_m": asset.elevation_m,
        "surveyed_on": asset.surveyed_on.isoformat(),
        "surveyor": asset.surveyor,
        "status": asset.status,
        "condition_score": asset.condition_score,
        "attributes": asset.attributes,
    }
    incoming = {key: value for key, value in payload.items() if value is not None}
    if "attribute_json" in incoming and "attributes" not in incoming:
        incoming["attributes"] = incoming["attribute_json"]
    current.update(incoming)
    result = validate_record(current, existing_ids=None, require_unique=False)
    if not result.ok:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": i.field, "reason": i.reason} for i in result.issues],
        )
    assert result.asset is not None
    persist_visit_and_update(db, asset, result.asset)
    db.commit()
    db.refresh(asset)
    return to_public(asset)


def delete_asset(db: Session, asset_id: str) -> str:
    asset = get_asset_or_404(db, asset_id)
    code = asset.asset_id
    db.delete(asset)
    db.commit()
    summary_cache.invalidate()
    return code


def list_visits(db: Session, asset_id: str) -> list[dict[str, Any]]:
    asset = get_asset_or_404(db, asset_id)
    visits = sorted(asset.visits, key=lambda item: item.surveyed_on)
    return [
        {
            "surveyed_on": visit.surveyed_on.isoformat(),
            "surveyor": visit.surveyor,
            "condition_score": visit.condition_score,
            "notes": visit.notes,
            "created_at": visit.created_at.isoformat() if visit.created_at else None,
        }
        for visit in visits
    ]


def _filtered_query(
    asset_type: str | None,
    status: str | None,
    surveyor: str | None,
    condition_min: int | None,
    condition_max: int | None,
    q: str | None,
) -> Select[tuple[Asset]]:
    stmt = select(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type.strip().lower())
    if status:
        stmt = stmt.where(Asset.status == status.strip().lower())
    if surveyor:
        stmt = stmt.where(Asset.surveyor.ilike(surveyor.strip()))
    if condition_min is not None:
        stmt = stmt.where(Asset.condition_score >= condition_min)
    if condition_max is not None:
        stmt = stmt.where(Asset.condition_score <= condition_max)
    if q:
        stmt = stmt.where(Asset.name.ilike(f"%{q.strip()}%"))
    return stmt.order_by(Asset.asset_id)


def list_assets(
    db: Session,
    *,
    asset_type: str | None = None,
    status: str | None = None,
    surveyor: str | None = None,
    condition_min: int | None = None,
    condition_max: int | None = None,
    q: str | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, int, int]:
    if limit is None:
        limit = DEFAULT_PAGE_LIMIT
    if limit < 1:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": "limit", "reason": "must be at least 1"}],
        )
    if limit > MAX_PAGE_LIMIT:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": "limit", "reason": f"must not exceed {MAX_PAGE_LIMIT}"}],
        )
    if offset < 0:
        raise AppError(
            status_code=422,
            error="validation_error",
            message="The request contents are invalid.",
            details=[{"field": "offset", "reason": "must be 0 or greater"}],
        )

    stmt = _filtered_query(asset_type, status, surveyor, condition_min, condition_max, q)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()
    return [to_public(row) for row in rows], total, limit, offset
