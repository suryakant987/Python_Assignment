from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from asset_registry.errors import AppError
from asset_registry.config import get_settings
from asset_registry.db.models import Asset, Visit
from asset_registry.domain.constants import ASSET_TYPES, condition_band
from asset_registry.domain.geo import haversine_km
from asset_registry.services.assets import to_public
from asset_registry.services.cache import summary_cache


def _compute_summary(db: Session) -> dict[str, Any]:
    assets = db.scalars(select(Asset)).all()
    by_type: list[dict[str, Any]] = []
    for asset_type in sorted(ASSET_TYPES):
        group = [item for item in assets if item.asset_type == asset_type]
        if not group:
            by_type.append(
                {
                    "asset_type": asset_type,
                    "surveyed": 0,
                    "average_condition": None,
                    "worst_asset_id": None,
                    "worst_condition": None,
                }
            )
            continue
        worst = min(group, key=lambda item: (item.condition_score, item.asset_id))
        average = sum(item.condition_score for item in group) / len(group)
        by_type.append(
            {
                "asset_type": asset_type,
                "surveyed": len(group),
                "average_condition": round(average, 2),
                "worst_asset_id": worst.asset_id,
                "worst_condition": worst.condition_score,
            }
        )

    lats = [item.latitude for item in assets]
    lons = [item.longitude for item in assets]
    extent = {
        "north": max(lats) if lats else None,
        "south": min(lats) if lats else None,
        "east": max(lons) if lons else None,
        "west": min(lons) if lons else None,
    }
    needing_repair = sum(
        1 for item in assets if item.status == "active" and item.condition_score < 5
    )
    surveyors = sorted({item.surveyor for item in assets})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "by_type": by_type,
        "extent": extent,
        "totals": {
            "assets": len(assets),
            "needing_repair": needing_repair,
            "surveyors": len(surveyors),
        },
        "needing_repair": needing_repair,
        "surveyors": surveyors,
    }


def get_summary(db: Session) -> tuple[dict[str, Any], bool]:
    cached = summary_cache.get()
    if cached is not None:
        payload = dict(cached)
        payload["from_cache"] = True
        return payload, True
    computed = _compute_summary(db)
    computed["from_cache"] = False
    summary_cache.set(computed, get_settings().summary_cache_seconds)
    return computed, False


def assets_needing_repair(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Asset)
        .where(Asset.status == "active", Asset.condition_score < 5)
        .order_by(Asset.condition_score, Asset.asset_id)
    ).all()
    return [to_public(row) for row in rows]


def most_visited(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    stmt = (
        select(Asset, func.count(Visit.id).label("visit_count"))
        .join(Visit, Visit.asset_pk == Asset.id)
        .group_by(Asset.id)
        .order_by(func.count(Visit.id).desc(), Asset.asset_id)
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [to_public(asset, visit_count=count) for asset, count in rows]


def nearest_asset(db: Session, latitude: float, longitude: float) -> dict[str, Any]:
    assets = db.scalars(select(Asset)).all()
    if not assets:
        raise AppError(
            status_code=404,
            error="not_found",
            message="No surveyed assets are stored yet.",
        )
    closest = min(
        assets,
        key=lambda item: haversine_km(latitude, longitude, item.latitude, item.longitude),
    )
    distance = haversine_km(latitude, longitude, closest.latitude, closest.longitude)
    return {"asset": to_public(closest), "distance_km": round(distance, 3)}


def surveyors_on(db: Session, surveyed_on: date) -> list[str]:
    rows = db.scalars(
        select(Asset.surveyor).where(Asset.surveyed_on == surveyed_on).distinct()
    ).all()
    visit_rows = db.scalars(
        select(Visit.surveyor).where(Visit.surveyed_on == surveyed_on).distinct()
    ).all()
    return sorted(set(rows) | set(visit_rows))


def condition_for(asset: Asset) -> str:
    return condition_band(asset.condition_score)
