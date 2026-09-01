# Architecture overview

## System diagram

```text
                    ┌─────────────────────────────────────────┐
                    │              Browser (React)             │
                    └───────────────────┬───────────────────────┘
                                        │
                          (Docker) Nginx : 8080
                     /api/* reverse-proxied  │  static assets served
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │           FastAPI backend : 8000          │
                    │  Zones · Alerts · Landslides · Rainfall   │
                    │  Terrain · Land Cover · Features · Risk   │
                    └──────┬───────────────────────┬───────────┘
                            │                       │
                            ▼                       ▼
                ┌───────────────────┐    ┌───────────────────────┐
                │ PostgreSQL+PostGIS │    │  Open-Meteo (live      │
                │  (or SQLite, dev)  │    │  weather, no API key)  │
                └───────────────────┘    └───────────────────────┘
                            ▲
                            │  POST /weather/refresh-all
                    ┌───────┴───────────┐
                    │  worker (optional) │   scheduled risk-update
                    │  Phase 16          │   cycle — separate process,
                    └────────────────────┘   never a loop in FastAPI
```

In local (non-Docker) development the browser talks to the FastAPI dev
server directly at `http://127.0.0.1:8000` and the frontend runs on Vite's
dev server (`http://localhost:5173`) — Nginx only exists in the Docker
deployment.

## Components

| Component | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React 19 + Vite, Tailwind v4, Leaflet, Recharts | Dashboard, Risk Map, Alert Center, Analytics, Risk Analysis, Data Sources, System Status |
| Backend | FastAPI + SQLAlchemy 2 + Pydantic v2 | REST API, risk engine, ingestion pipeline, spatial queries |
| Database | PostgreSQL 16 + PostGIS 3.4 (prod) / SQLite (dev) | Zones, alerts, historical events/observations, provenance, audit logs |
| ML | scikit-learn `RandomForestClassifier` | Demo-only risk classifier — see `backend/docs/ML_LIMITATIONS.md` |
| Worker (optional) | Plain Python script, Docker Compose `worker` profile | Scheduled `POST /weather/refresh-all` calls |
| Reverse proxy | Nginx (Docker only) | Static frontend + `/api/*` proxy, single origin for the browser |

## Data domains

| Domain | Model(s) | Real data status (as shipped) |
| --- | --- | --- |
| Zones (demo) | `Zone` | 7 seeded demo zones (`source_type=demo_seed`), always present |
| Alerts | `Alert` | Generated from zone risk; lifecycle: active → acknowledged → resolved (Phase 16) |
| Live weather | `WeatherObservation` | Real, from Open-Meteo, on demand (Phase 6) |
| Historical landslides | `LandslideEvent` | **Zero real events registered** — real ingestion pipeline exists (Phase 9/10) |
| Historical rainfall | `RainfallObservation` | **Zero real observations registered** — real ingestion + accumulation math exists (Phase 9/11) |
| Terrain | (no table — point query) | **No real DEM configured** — real point-extraction code exists (Phase 12), needs `rasterio` + a real DEM |
| Land cover | (no table — point query) | **No real raster configured** — real point-classification code exists (Phase 13), needs `rasterio` + a real raster + a recognized legend |
| Feature vectors | (no table — computed on demand, or via `scripts/build_feature_dataset.py`) | Combines whichever of the above are actually real; every field independently available/unavailable (Phase 14) |
| Risk-update audit | `RiskUpdateLog` | Real — every recomputation logged with its actual inputs (Phase 16) |
| Data provenance | `DataSource`, `IngestionRun` | Real, populated only by actual CLI ingestion (Phase 9) |

"Real data status" always reflects the *shipped* state — check
`GET /data-status` for the live truth at any time; a code path existing
is not the same as a real dataset being registered.

## Request flow: a risk score, end to end

1. `POST /weather/{zone_id}/refresh` (or the scheduled worker calling
   `POST /weather/refresh-all`) fetches current conditions from
   Open-Meteo.
2. `app/services/risk_update_service.compute_zone_risk` tries the
   RandomForest; on any failure, falls back to the deterministic
   rule-based engine. Both paths compute the same rule-based
   `risk_factors` breakdown regardless of which one actually set the
   score.
3. `reconcile_alerts` creates/supersedes/resolves the zone's `Alert` row
   (never deletes history) and records the reason (top contributing
   factor).
4. A `RiskUpdateLog` row captures the exact inputs, which fields were
   actually available, the prediction source, and the resulting score —
   independent of the `Alert`/`Zone` tables, so the history survives even
   if an alert is later superseded.

## Spatial query layer (Phases 10-11)

`app/services/spatial_service.py` is the single, model-agnostic
implementation behind every "nearby"/"map bounding box" endpoint
(`/landslides/nearby`, `/landslides/map`, `/rainfall/nearby`,
`/rainfall/map`). On PostgreSQL it uses real PostGIS functions
(`ST_DWithin`, `ST_Distance`, `ST_Intersects`); on SQLite it uses an
honestly-labeled fallback (`spatial_backend` in every response reads
`postgis`, `sqlite_exact`, or `sqlite_approximate`) — SQLite is never
presented as PostGIS-equivalent.

## Why a separate worker instead of a loop in FastAPI

FastAPI's request-handling process is designed to serve requests, not to
run a background `while True` loop — doing so risks blocking the event
loop, complicates graceful shutdown, and couples scheduling to API
uptime. `scripts/run_scheduled_risk_update.py` is a standalone process
(optionally run as the Docker Compose `worker` service, `--profile
worker`, not started by default) that calls the backend over plain HTTP
on an interval, with proper `SIGTERM`/`SIGINT` handling for clean
container shutdown.

## Full phase history

See the root [README.md](../README.md) for the phase-by-phase build log
(1 through 17) and [backend/docs/REAL_DATA_INGESTION.md](../backend/docs/REAL_DATA_INGESTION.md)
for the real-data ingestion architecture in detail.
