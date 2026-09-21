from asset_registry.api.routes.assets import router as assets_router
from asset_registry.api.routes.ingest import router as ingest_router
from asset_registry.api.routes.reports import router as reports_router
from asset_registry.api.routes.status import router as status_router

__all__ = ["assets_router", "ingest_router", "reports_router", "status_router"]
