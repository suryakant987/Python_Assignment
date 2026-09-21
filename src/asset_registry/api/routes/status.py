from datetime import datetime, timezone

from fastapi import APIRouter

from asset_registry.schemas import StatusResponse

router = APIRouter(tags=["Status"])


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Liveness check for the monitoring system",
    description="Unprotected. Exempt from the request rate limit.",
)
def status() -> dict:
    return {
        "status": "ok",
        "service": "asset-registry",
        "time": datetime.now(timezone.utc).isoformat(),
    }
