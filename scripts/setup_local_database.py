"""Create the local PostgreSQL role and databases for this project.

Reads POSTGRES_ADMIN_URL from .env (superuser connection to the
maintenance database), then creates:

  - role/user: asset_registry / assetreg123
  - database:  asset_registry
  - database:  asset_registry_test

Usage (from the project root, with venv active):

    python scripts/setup_local_database.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

try:
    import psycopg
    from psycopg import sql
except ImportError:
    print("psycopg is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

APP_USER = "asset_registry"
APP_PASSWORD = "assetreg123"
APP_DB = "asset_registry"
TEST_DB = "asset_registry_test"


def _to_psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def main() -> int:
    admin_url = os.getenv("POSTGRES_ADMIN_URL", "").strip()
    if not admin_url or "YOUR_POSTGRES_PASSWORD" in admin_url:
        print(
            "Set POSTGRES_ADMIN_URL in .env to your local postgres superuser URL.\n"
            "Example:\n"
            "  POSTGRES_ADMIN_URL=postgresql+psycopg://postgres:YourPassword@localhost:5432/postgres\n"
            "Use the password you chose when installing PostgreSQL on Windows."
        )
        return 1

    parsed = urlparse(_to_psycopg_url(admin_url))
    if not parsed.hostname:
        print("POSTGRES_ADMIN_URL is not a valid URL.")
        return 1

    print("Connecting as superuser to create role/databases...")

    try:
        with psycopg.connect(_to_psycopg_url(admin_url), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_USER,)
                )
                if cur.fetchone() is None:
                    cur.execute(
                        sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                            sql.Identifier(APP_USER),
                            sql.Literal(APP_PASSWORD),
                        )
                    )
                    print(f"Created role {APP_USER}")
                else:
                    cur.execute(
                        sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                            sql.Identifier(APP_USER),
                            sql.Literal(APP_PASSWORD),
                        )
                    )
                    print(f"Updated password for role {APP_USER}")

                for db_name in (APP_DB, TEST_DB):
                    cur.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
                    )
                    if cur.fetchone() is None:
                        cur.execute(
                            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                                sql.Identifier(db_name),
                                sql.Identifier(APP_USER),
                            )
                        )
                        print(f"Created database {db_name}")
                    else:
                        print(f"Database {db_name} already exists")
                    cur.execute(
                        sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                            sql.Identifier(db_name),
                            sql.Identifier(APP_USER),
                        )
                    )
    except psycopg.OperationalError as exc:
        print("\nCould not connect to PostgreSQL.")
        print(f"  {exc}")
        print(
            "\nChecklist:\n"
            "  1. PostgreSQL Server is installed (not only pgAdmin).\n"
            "  2. Windows service is Running (services.msc -> postgresql-x64-...).\n"
            "  3. Port matches postgresql.conf (this machine uses 5433).\n"
            "  4. POSTGRES_ADMIN_URL password matches the installer password.\n"
            "  5. In pgAdmin you can connect to Host=localhost Port=5433 User=postgres."
        )
        return 1

    print("\nDone. Next steps:")
    print("  1. Confirm DATABASE_URL in .env uses asset_registry / assetreg123")
    print("  2. alembic upgrade head")
    print("  3. python main.py")
    print("  4. In pgAdmin: refresh -> Databases -> asset_registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
