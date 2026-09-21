from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DurationMixin(BaseModel):
    duration_ms: float | None = None


class ErrorDetail(BaseModel):
    field: str
    reason: str


class ErrorBody(DurationMixin):
    error: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class TokenResponse(DurationMixin):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role: str = "surveyor"


class UserPublic(DurationMixin):
    username: str
    role: str
    created_at: datetime


class AssetBase(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    latitude: Any
    longitude: Any
    elevation_m: Any | None = None
    surveyed_on: Any
    surveyor: str
    status: str
    condition_score: Any
    attribute_json: Any | None = None
    attributes: dict[str, Any] | None = None


class AssetCreate(AssetBase):
    pass


class AssetReplace(AssetBase):
    pass


class AssetPatch(BaseModel):
    name: str | None = None
    asset_type: str | None = None
    latitude: Any | None = None
    longitude: Any | None = None
    elevation_m: Any | None = None
    surveyed_on: Any | None = None
    surveyor: str | None = None
    status: str | None = None
    condition_score: Any | None = None
    attribute_json: Any | None = None
    attributes: dict[str, Any] | None = None


class VisitPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    surveyed_on: datetime | str
    surveyor: str
    condition_score: int
    notes: str | None = None
    created_at: datetime | None = None


class AssetPublic(DurationMixin):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    elevation_m: float | None
    surveyed_on: str
    surveyor: str
    status: str
    condition_score: int
    attributes: dict[str, Any]
    condition_band: str
    visit_count: int | None = None


class AssetListResponse(DurationMixin):
    items: list[AssetPublic]
    total: int
    limit: int
    offset: int


class MessageResponse(DurationMixin):
    message: str
    asset_id: str | None = None


class IngestResponse(DurationMixin):
    rows_read: int
    rows_accepted: int
    rows_rejected: int
    rejects: list[dict[str, Any]] = Field(default_factory=list)


class TypeSummary(BaseModel):
    asset_type: str
    surveyed: int
    average_condition: float | None
    worst_asset_id: str | None
    worst_condition: int | None


class Extent(BaseModel):
    north: float | None
    south: float | None
    east: float | None
    west: float | None


class SummaryReport(DurationMixin):
    generated_at: str
    from_cache: bool = False
    by_type: list[TypeSummary]
    extent: Extent
    totals: dict[str, int]
    needing_repair: int
    surveyors: list[str]


class RepairListResponse(DurationMixin):
    items: list[AssetPublic]
    total: int


class NearestResponse(DurationMixin):
    asset: AssetPublic | None
    distance_km: float | None


class SurveyorDayResponse(DurationMixin):
    surveyed_on: str
    surveyors: list[str]


class StatusResponse(DurationMixin):
    status: str
    service: str
    time: str
