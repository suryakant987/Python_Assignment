from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from asset_registry.errors import AppError
from asset_registry.api.middleware import ProcessTimeMiddleware, RateLimitMiddleware
from asset_registry.api.routes import assets_router, ingest_router, reports_router, status_router
from asset_registry.auth.routes import router as auth_router
from asset_registry.auth.security import hash_password, verify_password
from asset_registry.config import get_settings
from asset_registry.db.models import User
from asset_registry.db.session import get_session_factory, init_db
from asset_registry.logging_setup import configure_logging


def _bootstrap_admin() -> None:
    """Create the bootstrap admin, or keep its password aligned with .env."""
    settings = get_settings()
    if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
        return
    session = get_session_factory()()
    try:
        user = (
            session.query(User)
            .filter(User.username == settings.bootstrap_admin_username)
            .one_or_none()
        )
        if user is None:
            session.add(
                User(
                    username=settings.bootstrap_admin_username,
                    password_hash=hash_password(settings.bootstrap_admin_password),
                    role="admin",
                )
            )
            session.commit()
            return

        if user.role != "admin":
            user.role = "admin"
        if not verify_password(settings.bootstrap_admin_password, user.password_hash):
            user.password_hash = hash_password(settings.bootstrap_admin_password)
        session.commit()
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _bootstrap_admin()
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="Utility Asset Registry",
        description=(
            "Cleans daily field-survey CSV exports, stores electricity-distribution "
            "assets, and serves them to authorised staff and the utility web map.\n\n"
            "Sign in at **POST /auth/login**, then click **Authorize** and paste "
            "`Bearer <token>`."
        ),
        version="1.0.0",
        contact={"name": "Asset Registry"},
        lifespan=lifespan,
    )

    app.add_middleware(ProcessTimeMiddleware)
    app.add_middleware(RateLimitMiddleware, exempt_paths={"/status"})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(status_router)
    app.include_router(auth_router)
    app.include_router(assets_router)
    app.include_router(reports_router)
    app.include_router(ingest_router)

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.as_dict())

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = error.get("loc", ())
            field = str(location[-1]) if location else "request"
            details.append({"field": field, "reason": error.get("msg", "is invalid")})
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "The request contents are invalid.",
                "details": details,
            },
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity(_request: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "The request contents are invalid.",
                "details": [{"field": "asset_id", "reason": "is already in use"}],
            },
        )

    return app


app = create_app()
