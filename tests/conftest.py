from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://asset_registry:change-me@localhost:5432/asset_registry_test",
)
os.environ.setdefault("JWT_SECRET", "unit-test-signing-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "test-admin-pass")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "0")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from asset_registry.auth.security import hash_password
from asset_registry.config import reset_settings_cache
from asset_registry.db.base import Base
from asset_registry.db.models import User
from asset_registry.db.session import get_db, reset_engine
from asset_registry.services.cache import summary_cache

ADMIN_PASSWORD = "test-admin-pass"
SURVEYOR_PASSWORD = "test-surveyor-pass"
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "survey_export.csv"


def _ensure_test_database() -> str:
    url = os.environ["DATABASE_URL"]
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    db_name = url.rsplit("/", 1)[-1]
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()
    return url


@pytest.fixture(scope="session")
def db_url() -> str:
    reset_settings_cache()
    return _ensure_test_database()


@pytest.fixture
def db_session(db_url: str) -> Generator[Session, None, None]:
    reset_engine()
    reset_settings_cache()
    summary_cache.invalidate()
    engine = create_engine(db_url, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    session.add(
        User(
            username="admin",
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
        )
    )
    session.add(
        User(
            username="surveyor1",
            password_hash=hash_password(SURVEYOR_PASSWORD),
            role="surveyor",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
        reset_engine()
        summary_cache.invalidate()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    from asset_registry.api.main import create_app

    app = create_app()

    def _override_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
