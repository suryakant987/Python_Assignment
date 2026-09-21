# Utility Asset Registry

Backend for a state electricity distribution utility. It takes the daily handheld GPS export, turns messy field rows into trusted asset records, stores them in PostgreSQL, and serves them over HTTP to authorised staff and to the utility web map.

There is no operator screen and no map to draw. This repository is the command-line ingestion tool and the web service.

## What it does

- Loads a day's CSV with one command
- Standardises descriptions, coordinates, asset types and surveyor names
- Rejects unusable rows into a rejects file with the reason (nothing is dropped silently)
- Stores accepted assets and their visit history in PostgreSQL
- Lets signed-in callers list, fetch, add, replace, correct and (admins) delete assets
- Serves summary, repair and visit reports, including a cached summary for the web map
- Restricts delete, bulk upload and user creation to administrators
- Publishes interactive API documentation at `/docs`

## Requirements

- Python 3.11 or later
- **PostgreSQL Server** installed locally (pgAdmin alone is not enough)

## Why pgAdmin showed no database

Earlier the API was connected to a temporary Docker Postgres on port 5432. That database does **not** appear as a normal local server in pgAdmin.

Your PostgreSQL 18 folder only had client tools (pgAdmin / binaries) and **no running Windows server / data directory**, so pgAdmin had nothing local to list.

Docker Postgres for this project has been removed. Use a real local PostgreSQL install.

## Local PostgreSQL + pgAdmin setup

1. Install **PostgreSQL Server** from https://www.postgresql.org/download/windows/  
   Remember the `postgres` superuser password from the installer.

2. Confirm the Windows service is running: `services.msc` → `postgresql-x64-18` (or similar) → **Running**.

3. Open **pgAdmin** → Register Server (if needed):
   - Host: `localhost`
   - Port: `5433` *(this project’s local PostgreSQL 18 uses 5433, not 5432)*
   - Username: `postgres`
   - Password: *(installer password)*

4. In the project `.env`, set your superuser URL (encode special characters in the password; `@` → `%40`):

```env
POSTGRES_ADMIN_URL=postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5433/postgres
DATABASE_URL=postgresql+psycopg://asset_registry:assetreg123@localhost:5433/asset_registry
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=Admin@123
```

5. Create the app role and databases:

```bash
python scripts/setup_local_database.py
```

Or run `scripts/init_local_database.sql` in pgAdmin Query Tool on the `postgres` database.

6. In pgAdmin, refresh **Databases** — you should see `asset_registry`.

## Python setup

```bash
copy .env.example .env
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python scripts/setup_local_database.py
alembic upgrade head
python main.py
```

On macOS or Linux: `python3 -m venv venv`, `source venv/bin/activate`, `cp .env.example .env`.

The first API start creates (or syncs) the bootstrap admin from `BOOTSTRAP_ADMIN_*`.

### Application login (API /docs)

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `Admin@123` |

Create surveyor accounts with `POST /auth/users` while signed in as admin.

### Database credentials (pgAdmin / DATABASE_URL)

| Item | Value |
|------|-------|
| Host | `localhost` |
| Port | `5433` |
| Database | `asset_registry` |
| User | `asset_registry` |
| Password | `assetreg123` |

## Ingestion tool

```bash
python -m asset_registry.ingest data/survey_export.csv
```

Optional arguments:

```text
python -m asset_registry.ingest --help
python -m asset_registry.ingest data/survey_export.csv --rejects outputs/rejects.csv --map outputs/assets.geojson --report outputs/summary.txt
python -m asset_registry.ingest data/survey_export.csv --strict
```

| File | Contents |
|------|----------|
| `outputs/rejects.csv` | Every refused row plus a `reason` column |
| `outputs/assets.geojson` | Accepted assets as a GeoJSON FeatureCollection |
| `outputs/summary.txt` | Printable summary by asset type, extent and totals |
| `logs/ingest.log` | One dated line per run, appended over time |

## Web service

```bash
python main.py
```

Open http://127.0.0.1:8000/docs  
Status (no login): http://127.0.0.1:8000/status  

Sign in with `POST /auth/login`, then use `Authorization: Bearer <token>`.

### Network operations

| Method | Path | Who | Purpose |
|--------|------|-----|---------|
| POST | `/auth/login` | anyone | Sign in |
| POST | `/auth/users` | admin | Create a user |
| GET | `/assets` | signed-in | List assets (filter, search, page) |
| GET | `/assets/{code}` | signed-in | Fetch one asset |
| POST | `/assets` | signed-in | Add a new asset |
| PUT | `/assets/{code}` | signed-in | Replace an asset in full |
| PATCH | `/assets/{code}` | signed-in | Correct selected fields |
| DELETE | `/assets/{code}` | admin | Remove an asset and its visit history |
| GET | `/assets/{code}/visits` | signed-in | Visit history |
| GET | `/reports/summary` | signed-in | Figures for the web map (cached 60s) |
| GET | `/reports/repairs` | signed-in | In-service assets with condition below 5 |
| GET | `/reports/most-visited` | signed-in | Assets visited most often |
| GET | `/reports/nearest` | signed-in | Nearest asset to a position |
| GET | `/reports/surveyors` | signed-in | Distinct surveyors on a given day |
| POST | `/ingest/upload` | admin | Bulk CSV upload |
| GET | `/status` | public | Monitoring heartbeat |

List query parameters: `type`, `status`, `surveyor`, `condition_min`, `condition_max`, `q`, `limit` (default 25, max 100), `offset`.

Moving to an enterprise database is a change of `DATABASE_URL` only.

## Tests

```bash
pytest
```

Uses throwaway database `asset_registry_test` — never the live `asset_registry` data.

## Project layout

```text
main.py                 start the API (uvicorn)
requirements.txt        pinned dependencies
.env / .env.example     secrets and DATABASE_URL (not committed)
scripts/
  setup_local_database.py   create local role + databases
  init_local_database.sql   same steps for pgAdmin Query Tool
src/asset_registry/
  config.py             loads .env from project root
  ingest/               CLI tool and CSV pipeline
  domain/               cleaning, validation, distance
  db/                   SQLAlchemy models and session
  api/                  FastAPI app, middleware, routes
  auth/                 passwords, credentials, roles
  services/             assets, reports, cache
data/                   sample handheld export
outputs/                rejects, map and summary from a run
tests/                  automated tests
```
