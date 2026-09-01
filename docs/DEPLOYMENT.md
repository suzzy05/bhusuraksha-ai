# Deployment guide

This describes the Phase 8 infrastructure: PostgreSQL + PostGIS, Alembic
migrations, and Docker Compose. **Local development without Docker still
works exactly as before** (SQLite, zero setup) — Docker/PostgreSQL is an
addition, not a replacement.

## Architecture

```text
React (Vite)  →  Nginx (static + /api reverse proxy)  →  FastAPI  →  PostgreSQL + PostGIS
```

In Docker, the browser only ever talks to Nginx (port 8080). Nginx serves
the built React app and proxies `/api/*` to the backend container over the
internal Docker network — the browser never needs to resolve Docker
service DNS names like `backend`, which it cannot do directly.

In local (non-Docker) development, the browser talks to the FastAPI dev
server directly (`http://127.0.0.1:8000`), same as every previous phase.

## Environment variables

| Variable | Used by | Purpose | Required? |
| --- | --- | --- | --- |
| `DATABASE_URL` | backend | `sqlite:///...` (default) or `postgresql+psycopg://user:pass@host:port/db` | No — defaults to SQLite |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | docker-compose (root `.env`) | Initializes the `db` container and composes `DATABASE_URL` for `backend` | Required for `docker compose up` |
| `WEATHER_PROVIDER` | backend | Live weather provider (Phase 6) | No — defaults to `open-meteo` |
| `CORS_ALLOWED_ORIGINS` | backend | Comma-separated allowed origins | No — defaults to local dev origins |
| `LOG_LEVEL` | backend | Python logging level | No — defaults to `INFO` |
| `VITE_API_BASE_URL` | frontend (build-time) | Where the frontend calls the API | No — `.env` for local dev, `/api` baked in for Docker |
| `BHUSURAKSHA_INDIA_BOUNDARY_PATH` | backend | Optional real India boundary file (Phase 7) | No |
| `BHUSURAKSHA_DEM_DATA_PATH` | backend | Optional real DEM GeoTIFF (Phase 12) — needs `rasterio` (`requirements-optional.txt`) installed too | No |
| `BHUSURAKSHA_LANDCOVER_PATH` / `BHUSURAKSHA_LANDCOVER_SCHEME` | backend | Optional real land-cover raster + which published legend to interpret it with (Phase 13) | No |
| `RISK_UPDATE_INTERVAL_SECONDS` | `worker` service (docker-compose) | Seconds between scheduled risk-update cycles (Phase 16) | No — defaults to `1800` |
| `LOG_SERVICE_NAME` | backend | Overrides the `service` field in structured JSON logs | No |

Copy `.env.example` → `.env` at the repo root (for Docker) and
`backend/.env.example` → `backend/.env` (for local dev) as needed. **Never
commit a real `.env` file** — both are gitignored.

## Local development (no Docker)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows; `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Uses SQLite (`backend/bhusuraksha.db`), auto-creates tables via
`create_all()`, and auto-seeds the 7 demo zones — unchanged from earlier
phases. `GET /health` reports `"database": {"connected": true, "type": "sqlite"}`.

## Docker Compose (PostgreSQL + PostGIS)

```bash
cp .env.example .env      # then set a real POSTGRES_PASSWORD
docker compose up --build
```

This starts, in order (via `depends_on: condition: service_healthy`):

1. **`db`** — `postgis/postgis:16-3.4`, persisted to the named volume
   `bhusuraksha_pgdata`. Host port `5433` (not `5432`, to avoid colliding
   with a native PostgreSQL install some machines already have listening
   on `5432` — this only affects host-side tools like `psql`; the backend
   always reaches it internally via `db:5432`).
2. **`backend`** — waits for `db` to be healthy, runs `alembic upgrade
   head`, then starts Uvicorn. Port `8000`.
3. **`frontend`** — Nginx serving the production React build, proxying
   `/api/*` to `backend:8000`. Port `8080`.

Open `http://localhost:8080`. `GET http://localhost:8000/health` (or
`http://localhost:8080/api/health`) reports
`"database": {"connected": true, "type": "postgresql", "postgis": {"available": true, "version": "..."}}`.

Stop with `docker compose down` (data persists); add `-v` only if you
intentionally want to wipe the database volume.

### Optional: scheduled risk-update worker (Phase 16)

Not started by a plain `docker compose up` — it's a separate opt-in
service (never a loop inside the FastAPI process itself):

```bash
docker compose --profile worker up -d worker
```

Calls `POST /weather/refresh-all` on an interval (`RISK_UPDATE_INTERVAL_SECONDS`,
default 1800s), logs each cycle as structured JSON, and exits cleanly on
`docker compose stop` (SIGTERM). A failed cycle (provider timeout, etc.)
is logged and retried next interval — it never crashes the container. For
a one-shot run from an external scheduler (cron, etc.) instead of a
long-lived container:

```bash
docker compose exec backend python scripts/run_scheduled_risk_update.py --once
```

## Database migrations (Alembic)

The `db` service and the Docker `backend` entrypoint run migrations
automatically. To run them manually (e.g. against a database you're
connecting to directly):

```bash
cd backend
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db   # PowerShell: $env:DATABASE_URL = "..."
alembic upgrade head
```

To create a new migration after changing a model:

```bash
alembic revision --autogenerate -m "describe the change"
```

**Always inspect the generated file before applying it** — autogenerate
against the `postgis/postgis` image's bundled `tiger_geocoder`/`topology`
extension tables is noisy; `alembic/env.py` already whitelists this
project's own tables (`OUR_TABLES`) to filter that out, but any new
migration should still be reviewed, not blindly trusted.

PostgreSQL deployments are migration-only — `Base.metadata.create_all()`
deliberately does not run against PostgreSQL (see `app/main.py`'s
`lifespan`), so a schema change always means a new Alembic revision.

## Seeding demo data

```bash
cd backend
python scripts/seed_database.py
```

Idempotent — running it any number of times seeds the same 7 demo zones
exactly once (`source_type="demo_seed"`) and never duplicates them or
touches `WeatherObservation`/`LandslideEvent` data. The app also seeds
automatically on startup (unchanged from earlier phases), so this script
is mainly useful for manual/CI seeding of a database the app hasn't
started against yet.

## Optional: migrating existing SQLite data to PostgreSQL

Only if you have real data in an existing `bhusuraksha.db` you want to
carry over (otherwise just let seeding populate a fresh PostgreSQL
database):

```bash
cd backend
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db

# Dry run first — shows record counts, migrates nothing:
python scripts/migrate_sqlite_to_postgres.py --sqlite-path bhusuraksha.db

# Then actually migrate:
python scripts/migrate_sqlite_to_postgres.py --sqlite-path bhusuraksha.db --confirm
```

This never runs automatically, never overwrites existing PostgreSQL data
silently (refuses unless `--force` is also passed), preserves row IDs and
foreign key relationships, and prints a before/after count summary for
every table so you can verify nothing was lost.

## Verifying PostGIS

```bash
docker compose exec db psql -U bhusuraksha -d bhusuraksha -c "SELECT PostGIS_Version();"
```

or via the API: `GET /health` includes `database.postgis.version` once
connected to PostgreSQL. `MonitoringRegion` and `LandslideEvent` each have
a `geom` column (SRID 4326, `POINT(longitude latitude)` — never swapped)
with a GIST index, auto-populated from `latitude`/`longitude` on
insert/update. This column only exists on PostgreSQL — SQLite models omit
it entirely (GeoAlchemy2's `Geometry` type requires SpatiaLite, which
local development deliberately does not install).

## Backup strategy (PostgreSQL)

```text
Database  →  pg_dump  →  secure storage (off-host)
```

```bash
docker compose exec db pg_dump -U bhusuraksha bhusuraksha > backup_$(date +%Y%m%d).sql
```

Restore with `psql -U bhusuraksha -d bhusuraksha < backup_20260101.sql`
against a fresh, migrated database. This phase documents the workflow
only — no automatic/scheduled cloud backup is configured.

## Upgrade process

1. Pull the new code.
2. `docker compose build` (or rebuild the changed service only).
3. `docker compose up -d` — `db` health-gates `backend`, which runs any
   new Alembic migrations before serving traffic.
4. Verify `GET /health` reports `connected: true` and, on PostgreSQL,
   `postgis.available: true`.

## Known limitations

- `MonitoringRegion`/`LandslideEvent`/`RainfallObservation` tables are
  empty by default (no synthetic data, per the project's data-honesty
  rules) — populating them requires real registered datasets (see
  `backend/docs/REAL_DATA_INGESTION.md`).
- Terrain (Phase 12) and land cover (Phase 13) point queries need the
  optional `rasterio` package (`pip install -r requirements-optional.txt`,
  not part of the base Docker image) AND a real configured raster —
  without both, they honestly report unavailable rather than estimating.
- No automated backup scheduling, connection pooling service (e.g.
  PgBouncer), or read replicas — out of scope for this phase.
- The `worker` service (Phase 16) is a single instance with no leader
  election — running more than one would duplicate refresh cycles. Fine
  for this project's scale; would need locking for true horizontal scale.
