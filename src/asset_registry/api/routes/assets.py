from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from asset_registry.auth.deps import get_current_user, require_admin
from asset_registry.db.models import User
from asset_registry.db.session import get_db
from asset_registry.domain.constants import DEFAULT_PAGE_LIMIT
from asset_registry.schemas import AssetCreate, AssetListResponse, AssetPatch, AssetPublic, AssetReplace, MessageResponse
from asset_registry.services import assets as asset_service

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get(
    "",
    response_model=AssetListResponse,
    summary="List assets",
    description="Returns one page of assets. Narrow by type, status, surveyor, condition range or a word in the description.",
)
def list_assets(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    asset_type: str | None = Query(default=None, alias="type"),
    status: str | None = None,
    surveyor: str | None = None,
    condition_min: int | None = None,
    condition_max: int | None = None,
    q: str | None = Query(default=None, description="Case-insensitive word in the description"),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items, total, limit, offset = asset_service.list_assets(
        db,
        asset_type=asset_type,
        status=status,
        surveyor=surveyor,
        condition_min=condition_min,
        condition_max=condition_max,
        q=q,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/{asset_id}",
    response_model=AssetPublic,
    summary="Fetch one asset by its code",
)
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    asset = asset_service.get_asset_or_404(db, asset_id)
    return asset_service.to_public(asset)


@router.get(
    "/{asset_id}/visits",
    summary="Visit history for one asset",
)
def get_visits(
    asset_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {"asset_id": asset_id.upper(), "visits": asset_service.list_visits(db, asset_id)}


@router.post(
    "",
    response_model=AssetPublic,
    status_code=201,
    summary="Add a new asset",
)
def add_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload = body.model_dump()
    if payload.get("attributes") is None:
        payload["attributes"] = payload.get("attribute_json")
    return asset_service.create_asset(db, payload)


@router.put(
    "/{asset_id}",
    response_model=AssetPublic,
    summary="Replace an existing asset in full",
)
def replace_asset(
    asset_id: str,
    body: AssetReplace,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload = body.model_dump()
    if payload.get("attributes") is None:
        payload["attributes"] = payload.get("attribute_json")
    return asset_service.replace_asset(db, asset_id, payload)


@router.patch(
    "/{asset_id}",
    response_model=AssetPublic,
    summary="Correct selected fields of an existing asset",
)
def patch_asset(
    asset_id: str,
    body: AssetPatch,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_unset=True)
    return asset_service.patch_asset(db, asset_id, payload)


@router.delete(
    "/{asset_id}",
    response_model=MessageResponse,
    summary="Remove an asset and its visit history (administrator only)",
)
def remove_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    code = asset_service.delete_asset(db, asset_id)
    return {"message": f"Asset {code} was deleted.", "asset_id": code}
