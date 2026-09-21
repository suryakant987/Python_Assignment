from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from asset_registry.auth.deps import get_current_user
from asset_registry.db.models import User
from asset_registry.db.session import get_db
from asset_registry.schemas import NearestResponse, RepairListResponse, SummaryReport, SurveyorDayResponse
from asset_registry.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/summary",
    response_model=SummaryReport,
    summary="Summary figures for the web map",
    description="Cached for up to 60 seconds. The cache is discarded as soon as any asset is added, corrected or removed.",
)
def summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    payload, _from_cache = report_service.get_summary(db)
    return payload


@router.get(
    "/repairs",
    response_model=RepairListResponse,
    summary="Assets still in service whose condition is below 5",
)
def repairs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    items = report_service.assets_needing_repair(db)
    return {"items": items, "total": len(items)}


@router.get(
    "/most-visited",
    summary="Assets visited most often",
)
def most_visited(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    items = report_service.most_visited(db, limit=limit)
    return {"items": items, "total": len(items)}


@router.get(
    "/nearest",
    response_model=NearestResponse,
    summary="Surveyed asset nearest to a position",
)
def nearest(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    return report_service.nearest_asset(db, latitude, longitude)


@router.get(
    "/surveyors",
    response_model=SurveyorDayResponse,
    summary="Distinct surveyors who worked on a given day",
)
def surveyors(
    on: date,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    names = report_service.surveyors_on(db, on)
    return {"surveyed_on": on.isoformat(), "surveyors": names}
