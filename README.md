# BHUSURAKSHA AI

### Predict. Warn. Protect.

An AI-powered landslide early warning and risk monitoring platform.

## Phase 1 — Backend Foundation

Phase 1 delivers a working FastAPI backend: SQLite database, zone/alert
models, deterministic risk scoring engine, automatic demo data seeding, and
REST APIs with Swagger docs.

## Phase 2 — Machine Learning Risk Prediction

Phase 2 adds a `RandomForestClassifier` trained on a small synthetic/demo
dataset. `POST /predict-risk` uses the ML model when available and
transparently falls back to the Phase 1 rule-based engine otherwise — see
[backend/README.md](backend/README.md) for training and API details.

## Phase 3 — Real Data & Geospatial Pipeline

Phase 3 adds a modular pipeline (`backend/geospatial/`) for ingesting real
external geospatial datasets (historical landslide inventories, rainfall,
DEM, vegetation) — CSV/GeoJSON loaders, column-mapping, validation,
normalization, and data-quality scoring — while keeping demo and real data
clearly separated. See [backend/docs/DATA_SOURCES.md](backend/docs/DATA_SOURCES.md).

## Phase 4 — Frontend Foundation & Dashboard

Phase 4 adds a React + Vite dashboard (`frontend/`) — Dashboard, Risk Map,
Alerts, Analytics, and Data Status pages, all driven by the live backend
API with explicit loading/error/empty states. See
[frontend/README.md](frontend/README.md).

## Phase 5 — Interactive GIS Risk Map

Phase 5 upgrades the Risk Map page into an interactive Leaflet/OpenStreetMap
view (`frontend/src/components/map/`) — real zone coordinates from
`GET /zones`, risk-colored markers, popups, a risk-level filter, a
sortable zone list panel, and active-alert indicators, with no API key
required.

## Phase 6 — Live Weather Integration & Risk Updates

Phase 6 adds a modular live weather layer (`backend/app/services/weather_service.py`,
backed by the free Open-Meteo API, no key required). `POST /weather/{zone_id}/refresh`
and `POST /weather/refresh-all` fetch real current conditions, update only
the fields actually returned (existing data is preserved otherwise), store
a `WeatherObservation`, recompute risk (ML-first, rule-based fallback, no
retraining), and reconcile alerts without duplicates. The frontend exposes
this via a Live Weather + Weather History section in zone details and a
"Refresh Environmental Data" button on the Dashboard. See
[backend/docs/WEATHER_LIMITATIONS.md](backend/docs/WEATHER_LIMITATIONS.md)
for why current weather alone isn't a validated landslide forecast.

## Phase 7 — Pan-India Real Data Foundation & Scalable Monitoring

Phase 7 adds the architecture for scaling coverage across India —
`MonitoringRegion` and `LandslideEvent` models, a paginated
`GET /landslides` API, a provenance registry (`backend/geospatial/source_registry.py`
+ `scripts/register_data_source.py`), and documented (not-yet-implemented)
extension points for a real DEM and historical rainfall dataset. It does
**not** claim the system currently monitors all of India — `GET /india/summary`
and the Dashboard's India Monitoring Overview report real counts only,
starting at `coverage_status: "prototype"` until real regional data and
historical events actually exist. Existing demo zones are explicitly
tagged `source_type="demo_seed"`, distinct from `external_real` and
`derived`, so demo and real data are never mixed silently.

## Phase 8 — Production Infrastructure: PostgreSQL + PostGIS + Docker

Phase 8 adds PostgreSQL + PostGIS support, Alembic migrations, and Docker
Compose for `db` + `backend` + `frontend` — **local SQLite development is
unchanged and does not require Docker**. Full details, environment
variables, and troubleshooting: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Architecture

```text
React (Vite)  →  Nginx (static + /api proxy)  →  FastAPI  →  PostgreSQL + PostGIS
```

### Local development (no Docker — unchanged from earlier phases)

```bash
cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Uses SQLite by default; nothing here requires Docker or PostgreSQL.

### Docker development

```bash
cp .env.example .env      # set a real POSTGRES_PASSWORD
docker compose up --build
```

Opens at `http://localhost:8080` (frontend, proxying `/api` to the
backend); backend directly at `http://localhost:8000`.

### Database migrations

```bash
cd backend
alembic upgrade head
```

### Seeding

```bash
python scripts/seed_database.py
```

Idempotent — safe to run repeatedly; never duplicates the 7 demo zones.

### Optional SQLite → PostgreSQL migration

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite-path bhusuraksha.db --confirm
```

Never runs automatically; refuses to overwrite existing PostgreSQL data
unless `--force` is also passed.

### PostGIS verification

```bash
docker compose exec db psql -U bhusuraksha -d bhusuraksha -c "SELECT PostGIS_Version();"
```

`GET /health` also reports `database.postgis.version` once connected to
PostgreSQL.

## Phase 9 — Real Data Acquisition & Ingestion Platform

Phase 9 adds a real-data ingestion pipeline (`backend/ingestion/`) — CLI
registration, SHA-256 checksums, flexible column-alias mapping,
conservative duplicate detection, batched inserts, and a full audit trail
(`DataSource` + `IngestionRun`). It does **not** train a new ML model or
claim nationwide coverage — as shipped, zero real datasets are
registered; check `GET /data-status`'s `real_data` block for the live
truth. Full details: [backend/docs/REAL_DATA_INGESTION.md](backend/docs/REAL_DATA_INGESTION.md).

```bash
cd backend
python scripts/ingest_dataset.py --category historical_landslide --path data/raw/external/landslides.csv --name "My Dataset"
python scripts/list_data_sources.py
python scripts/inspect_dataset.py path/to/data.csv
```

Real point-in-polygon state/district enrichment (pure Python, no new
dependency) activates only when a real boundary GeoJSON is configured
(`BHUSURAKSHA_STATE_BOUNDARY_PATH` / `BHUSURAKSHA_DISTRICT_BOUNDARY_PATH`)
— otherwise those fields stay whatever the source data provided, or
`null`. **REGISTERED DATA ≠ VALIDATED ML DATA**, and **DATA COVERAGE ≠
RISK LEVEL** — see the docs for why.

Authentication, real national dataset ingestion at scale, and real ML
training on production data are planned for later phases.

## Phase 9.6 — Professional Frontend UI/UX Redesign

Phase 9.6 redesigns the frontend into a GIS/emergency-monitoring-grade
UI — a grouped, collapsible sidebar (Overview / Intelligence / Data), a
map-first Dashboard with an honest prototype-status banner, a redesigned
Alert Center (Active/History tabs), a new dedicated Risk Analysis page
that separates a prediction's local rule-based factors from the ML
model's *global* feature importance (never conflated), a new Data
Sources page, and a reframed System Status page (Operational /
Unavailable / Not Configured / Degraded, only ever set from a real API
response). No backend logic changed beyond one additive `GET
/alerts?status=` parameter.

## Phase 9.7 — Frontend Performance Optimization & Final Polish

Phase 9.7 adds route-level code splitting (`React.lazy` + `Suspense`,
Dashboard eager, every other page lazy), defers Leaflet and Recharts out
of the initial bundle even on the eager Dashboard (its own map/chart are
independently lazy-loaded), a reusable `PageErrorBoundary` (a crash in
one page never takes down the app shell), and a 404 page. Cut the
production main JS chunk from 935 KB to 309 KB (gzipped 279 KB → 99 KB).
Also fixed a real duplicate-request bug found in the process: `Sidebar`
and `Topbar` were each independently polling `GET /health`.

## Phase 10 — Real Historical Landslide Data Integration

Phase 10 adds bounded, read-only spatial query APIs on top of Phase 9's
`LandslideEvent`/PostGIS foundation — `GET /landslides/nearby` (radius
search) and `GET /landslides/map` (viewport bounding box), plus `GET
/data-sources/{id}/quality` (record-completeness — explicitly "Data
Completeness", never "accuracy"). PostGIS is used for real spatial
queries on PostgreSQL (`ST_DWithin`/`ST_Distance`/`ST_Intersects`);
SQLite gets an honestly-labeled fallback (`spatial_backend` in every
response reads `postgis`, `sqlite_exact`, or `sqlite_approximate` — never
pretends SQLite has PostGIS). The Risk Map gained a real "Historical
Landslides" layer with `leaflet.markercluster` clustering, an event
detail modal, and state/source/date filters. **As shipped, zero real
historical landslide datasets are registered** — verified honestly at
every layer (map, Analytics, Data Sources) and, separately, functionally
verified end-to-end (SQLite, real PostgreSQL+PostGIS, and Docker) using
the existing `tests/fixtures/landslides_test.csv` **test fixture**,
which was removed again afterward. Full details:
[backend/docs/REAL_DATA_INGESTION.md](backend/docs/REAL_DATA_INGESTION.md).

## Phase 11 — Real Historical Rainfall Intelligence

Phase 11 adds real rainfall-accumulation intelligence on top of Phase
9's `RainfallObservation` model (which gained a `station_id` column via
migration). `GET /rainfall/summary?lat=&lon=&radius_km=` computes
24h/72h/7d/30d accumulation and an antecedent-rainfall index from the
single **nearest real station** within range — never summed across
distinct stations, and every window is `null` (never `0`) unless a real
observation actually falls inside it. Also added: `GET
/rainfall/nearby`, `GET /rainfall/map`, `GET /rainfall/history`, sharing
the same honestly-labeled PostGIS/SQLite-fallback spatial layer Phase 10
introduced (now generalized for both models). The Risk Map gained a
"Rainfall" layer with clustering and a detail modal. **As shipped, zero
real rainfall datasets are registered** — verified honestly at every
layer and, separately, functionally verified end-to-end (SQLite, real
PostgreSQL+PostGIS) using the existing `tests/fixtures/rainfall_test.csv`
test fixture, removed again afterward. Full details:
[backend/docs/REAL_DATA_INGESTION.md](backend/docs/REAL_DATA_INGESTION.md).

## Phase 12 — Terrain & DEM Intelligence

Phase 12 adds real, point-level DEM elevation/slope/aspect extraction
(`GET /terrain/features?lat=&lon=`, `app/services/terrain_service.py`)
using Horn's method (the same algorithm most desktop GIS "Slope" tools
use) — gated on the optional `rasterio` package
(`backend/requirements-optional.txt`, **not** installed in the base
Docker image) and a real configured DEM (`BHUSURAKSHA_DEM_DATA_PATH`).
**No real DEM is configured as shipped** — verified with a synthetic
test GeoTIFF fixture (`tests/fixtures/dem_test.tif`, a known uniform
slope) against an analytically-computed expected value (~26.57°); a real
correctness bug (raw DEM pixel resolution in degrees, not meters, being
fed directly into the slope formula) was caught and fixed during that
verification.

## Phase 13 — Land Cover Intelligence

Phase 13 adds real point-level land-cover classification (`GET
/landcover?lat=&lon=`, `app/services/landcover_service.py`), mapping a
raster's raw class code to a normalized category
(forest/grassland/cropland/urban/bare_land/water/unknown) via a real,
published legend (ESA WorldCover — `geospatial/landcover_schemes.py`),
but only when `BHUSURAKSHA_LANDCOVER_SCHEME` names a recognized scheme —
an unset or unrecognized scheme returns the raw code with
`normalized_category: "unknown"` rather than guessing. Same
`rasterio`-optional, DEM-style gating as Phase 12. **No real land-cover
raster is configured as shipped** — verified with a synthetic test
raster fixture (`tests/fixtures/landcover_test.tif`).

## Phase 14 — Unified Landslide Feature Engineering

Phase 14 combines Phases 10-13 into one feature vector per point-in-time
coordinate (`GET /features?lat=&lon=&as_of=`,
`app/services/feature_engineering_service.py`): rainfall accumulation,
terrain, land cover, and historical-landslide density (a genuinely real,
always-computed PostGIS/SQLite query — 0 nearby events is a real result,
never "unavailable"). Every other feature is independently
available/unavailable — never a fabricated 0 substituting for missing
data. `scripts/build_feature_dataset.py` builds a reproducible CSV +
metadata JSON from all registered `LandslideEvent` rows for future ML
work; with zero real events registered (as shipped), it honestly produces
an empty dataset rather than fabricating rows — verified with the same
test fixtures used in Phases 10-11, confirming correct real rainfall
accumulation and historical-density values in the output, then removed.

## Phase 15 — Real Machine Learning Pipeline: STOPPED

**Not started.** Phase 15 explicitly requires sufficient real,
registered historical landslide data before any real training may begin.
As of Phase 14, zero real datasets are registered — see
`GET /data-status` for the live truth. No dataset splitting, no model
training, and no evaluation against real-world outcomes has been
performed. The Phase 2 synthetic demo model is unchanged and remains
clearly labeled as such — see
[backend/docs/ML_LIMITATIONS.md](backend/docs/ML_LIMITATIONS.md) for the
complete, current picture.

## Phase 16 — Operational Monitoring & Alert Workflow

Phase 16 adds a real alert lifecycle (`Alert.status`:
active → acknowledged → resolved, via new `POST /alerts/{id}/acknowledge`
/ `/resolve` endpoints — never deletes an alert, only supersedes it) and
an auditable `RiskUpdateLog` recording every risk recomputation's real
inputs, data availability, and prediction source
(`GET /zones/{id}/risk-updates`). A found-and-fixed real bug: `alert.py`'s
route module wasn't previously distinguishing "acknowledged" from
resolved. Scheduled updates run via `scripts/run_scheduled_risk_update.py`
— a standalone process (never a loop inside FastAPI) with real
`SIGTERM`/`SIGINT` handling, wired as an **optional** Docker Compose
`worker` service (`docker compose --profile worker up -d worker`, not
started by default). Also upgraded backend logging to genuine structured
JSON (`app/logging_config.py`) as part of this work.

## Phase 17 — Production Deployment

Phase 17 hardens BHUSURAKSHA for real deployment: a security pass found
no hardcoded secrets/passwords/API keys (`.env` confirmed gitignored,
`GET /health` confirmed to never expose `DATABASE_URL`), added
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[backend/docs/ML_LIMITATIONS.md](backend/docs/ML_LIMITATIONS.md), and
updated [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the Phase 12/13
optional-dependency pattern and the Phase 16 worker service. Backup
strategy (`pg_dump`, documented in Phase 8) and health reporting
(`GET /health`) were already real and are unchanged — this phase did not
fabricate new claims for either. **India-wide monitoring, validated ML
prediction accuracy, and fully-populated real terrain/land-cover/rainfall
coverage are still not claimed anywhere in the system** — see each
phase's own honesty notes above and `GET /data-status` for the always-live
truth.

## Phase 18 — First Real Historical Landslide Dataset

Phase 18 registers and ingests BHUSURAKSHA's first real dataset via the
Phase 9 pipeline: the **NASA Global Landslide Catalog Export** (NASA
Goddard Space Flight Center, public domain, 1970-2016 snapshot,
11,033 events globally) — `python scripts/ingest_dataset.py --category
historical_landslide ...`, verified end-to-end with 0 rejected rows and 0
duplicates, and idempotency-checked (re-running the same file inserts 0
new rows). `GET /data-status`'s `india_monitoring.coverage_status`
correctly flips from `prototype` to `regional_real_data` as a direct,
honest consequence — not a hardcoded claim. Full provenance recorded in
[backend/docs/DATA_SOURCES.md](backend/docs/DATA_SOURCES.md).

Two real bugs were found and fixed while verifying this dataset ingested
correctly (not just "some rows in"): `ingestion/validation.parse_date_safely`
was missing the `MM/DD/YYYY hh:mm:ss AM/PM` format this dataset actually
uses, silently nulling every `event_date`; and
`ingestion/processors/landslides.py`'s column-alias table never actually
included `state`/`district` aliases despite this document previously
claiming it did — both fixed, and the dataset was deleted and re-ingested
cleanly (not patched in place) once fixed, then re-verified. **Still
true, unchanged by this phase:** no ML retraining occurred (Phase 15
remains stopped), and this is one dataset with global — not India-only —
coverage; see `GET /data-status` for the always-live truth.

## Phase 19 — Retire the Synthetic Demo ML Model

Phase 19 retires the Phase 2 demo `RandomForestClassifier`: its trained
artifacts (`ml/artifacts/landslide_model.joblib`, `model_metadata.json`)
and the synthetic dataset that produced them
(`data/raw/demo/landslide_training_data.csv`,
`data/processed/landslide_training_data_processed.csv`) were deleted.
`ml/predict.is_model_available()` now always returns `False`, so every
prediction — verified live via `POST /predict-risk` and `GET
/data-status` after a backend restart — correctly and transparently
reports `prediction_source: "rule_based_fallback"`, `model_available:
false`. **This does not mean the app now trains or predicts on real
data**: the real 11,033-event catalog from Phase 18 has no `risk_level`
labels, no negative (non-landslide) samples, and no joined
rainfall/terrain/vegetation features, so it is not a valid supervised
training set as-is — see
[backend/docs/ML_LIMITATIONS.md](backend/docs/ML_LIMITATIONS.md) for why.
Phase 15 remains explicitly stopped. The 7 demo `Zone` rows are
unchanged and still power the Dashboard/Risk Map/Alerts — no real
monitoring-region dataset exists to replace them yet.

## Phase 20 — Susceptibility-Modeling Pipeline (Plumbing)

Phase 20 builds the real, standard methodology Phase 15 was waiting for:
landslide susceptibility via presence/pseudo-absence modeling, rather than
a fabricated classifier on labels that don't exist. New:
`app/services/negative_sampling_service.py` (real-coordinate pseudo-absence
generation — buffer exclusion around real events, real-boundary filtering,
stratified against the study area's own real terrain distribution),
`scripts/build_susceptibility_dataset.py` (sibling to the untouched Phase 14
`build_feature_dataset.py`), and `ml/susceptibility/` (time-based train/test
split, PR-AUC/precision/recall, a historical-density ablation, and
`GET /susceptibility` — always disclosing `prediction_source:
"susceptibility_ml"`, permanently distinct from the retired demo model's
`"machine_learning"` value). Verified end-to-end this session with synthetic
fixtures temporarily ingested and a fixture DEM/land-cover raster
temporarily configured, then removed again — this proves the plumbing, **it
does not mean a real model exists**: `ml/susceptibility/artifacts/` is
empty and `GET /susceptibility` always returns `model_available: false` as
shipped. Real training needs a real DEM + land-cover raster + rainfall data
for a real study area (recommended pilot: Uttarakhand + Himachal Pradesh)
and a real state-boundary file — none of that has been acquired yet. See
[backend/docs/ML_LIMITATIONS.md](backend/docs/ML_LIMITATIONS.md).

## Phase 21 — Real Zones Derived from Real Historical Events

Phase 21 adds 27 new `Zone` rows (`source_type="derived"`), one per Indian
state with real Phase 18 events (890 real events across 27 states/UTs,
matched against the real Natural Earth boundary file, not a second
hardcoded list) — real centroid coordinates, a real
`historical_event_count`, alongside the 7 untouched demo zones (34 total).
**Deliberately never given a fabricated risk score**: `risk_score=0.0`,
`risk_level="UNKNOWN"` (a value the frontend already renders as a distinct
neutral badge), because the rule-based engine needs real rainfall/slope/
elevation this project doesn't have for most of India — feeding it
placeholder environment values would produce a plausible-looking but
entirely invented number. `GET /zones/{id}` skips rule-based computation
entirely for `derived` zones (`risk_factors` returned as honest all-zero,
never contradicting the 0.0/UNKNOWN top-level fields), and
`risk_update_service.update_zone_risk()` is a guarded no-op for them so a
weather refresh or the scheduled worker can never silently overwrite
UNKNOWN with a fabricated score — live weather refresh (`POST
/weather/refresh-all`) still updates their real rainfall/humidity/
temperature fields, since that part is genuinely real. Frontend
(`ZonePopup`, `ZoneDetailModal`, the Risk Map zone list) shows "N
historical event(s) recorded" instead of a risk score wherever
`risk_level === "UNKNOWN"`. Migration: `alembic/versions/a1b2c3d4e5f6_*.py`
adds `zones.historical_event_count` (nullable).

## Phase 22 — Real Susceptibility Model (Uttarakhand + Himachal Pradesh Pilot)

Phase 22 completes Phase 20's plumbing with a genuinely trained model,
using three real, freely-obtained sources: **Copernicus DEM GLO-30** (AWS
Open Data, 32/42 tiles — 10 failed on transient DNS errors and were not
force-retried further), **ESA WorldCover 10m 2021** (AWS Open Data, full
9/9 tiles), and **IMD's public gridded daily rainfall**
(imdpune.gov.in's own web form, no login — 58,016 real rows extracted at
the exact coordinates/dates 462 real events and 1,386 generated negatives
actually needed, not the full national grid). Result: **PR-AUC 0.805,
ROC-AUC 0.946** on a real time-based test split (1,782 rows total,
split at 2015-08-03); the historical-density-ablation still scores PR-AUC
0.67, showing real skill from terrain/rainfall alone. Verified live: `GET
/susceptibility` scores a real training-set event coordinate 97.9/100 and
a real negative-sample coordinate (winter, dry, high-altitude) 1.0/100.

Two real bugs found and fixed while building this: `terrain_service.py`/
`landcover_service.py` were reading an **entire raster band into memory on
every single point query** — harmless against the small Phase 12/13 test
fixtures, but a severe real-world performance bug against an actual
DEM/land-cover mosaic (a bulk sampling run that should take seconds was
still running after 20+ minutes before this fix; a single point query
went from 12+ seconds to 0.07 seconds) — now windowed single/3×3-pixel
reads. And `build_susceptibility_dataset.py`'s row-validity check only
verified `rainfall_available` (whether IMD found ANY nearby station) not
each specific window, so a row could silently pass with a `null
rainfall_24h` if only its 30-day window had data — now every numeric
field actually used for training is checked individually.

**Still not India-wide** — this is a two-state pilot; see
[backend/docs/ML_LIMITATIONS.md](backend/docs/ML_LIMITATIONS.md) for the
full, current picture, including why this was never wired into zone-level
`/predict-risk`.

## Phase 23 — Real Geographic Clustering + Real Terrain for Zones

Phase 23 rebuilds Phase 21's one-zone-per-state derived zones into
**78 real zones** (up from 27) using DBSCAN — a real, standard clustering
algorithm, not an invented heuristic — on each state's actual event
coordinates (`--cluster-eps-km 60`), so e.g. Andhra Pradesh's 21 real
events become 9 real sub-regional zones instead of one. New Zone column
`terrain_data_real` (migration `b2c3d4e5f6a7`): **True only for zones whose
real coordinates fall inside the Pilot DEM's real coverage** (4 of 78 —
Uttarakhand, Himachal Pradesh, Haryana, one Uttar Pradesh cluster, all
near the Phase 22 pilot bbox) — for those, `slope`/`elevation` are real
values read from the real DEM (never guessed), and
`risk_update_service.update_zone_risk()`/`GET /zones/{id}` both stop
treating the zone as a fabrication risk once real terrain + real live
weather (Phase 6) are both present — `POST /weather/refresh-all` now
computes a genuine rule-based risk score for those 4 zones (verified live:
Uttarakhand's cluster scores 44.18/100 MODERATE from real slope=22.3°,
elevation=1241m, live rainfall=23.6mm, live humidity=98%; only
`vegetation` stays the documented 0.5 neutral default, same as every zone
including the original demo ones). The other 74 zones — outside real DEM
coverage — correctly remain `risk_level: "UNKNOWN"`, unchanged from Phase
21. Total zones: 7 demo + 78 derived = **85**.

## Phase 24 — Real Terrain for Every Zone (Targeted, Not a Full-Country Download)

Phase 24 replaces "4 of 78 zones have real terrain" with **all 85**, using
a real insight rather than a bigger download: since each zone only needs
its own coordinate's DEM tile — not a contiguous mosaic — 74 remaining
zones needed only **70 unique 1°×1° Copernicus DEM tiles** (~2.8GB), not
the ~800-tile / 30GB+ full-India mosaic Phase 20 correctly flagged as
disk-infeasible. New `scripts/enrich_zones_with_real_terrain.py`
downloads (and caches) exactly the tile each zone's real coordinate falls
in, reads a real 3×3-pixel neighborhood there via the same Horn's-method
code `terrain_service.py` uses for live serving (imported directly, not
reimplemented), and sets real `slope`/`elevation`/`terrain_data_real=True`.
One zone hit a transient network timeout on its tile and was retried
successfully; every other zone got real data on the first pass — no zone
was ever given a fabricated value for a tile that didn't download.
`POST /weather/refresh-all` afterward computed genuine rule-based risk for
all 85 zones (78 real + 7 reference) — **zero remain UNKNOWN**: 78
MODERATE, 6 HIGH, 1 LOW, generating 3 new real alerts (Mizoram Region 1,
Arunachal Pradesh Regions 2/3) alongside the original 3 demo-zone alerts.

## Phase 25 — Real-Data-Grounded Assistant

Phase 25 adds `GET /assistant/ask?q=...` and a floating chat widget
(bottom-right, every page) answering common questions ("which place is
riskiest", "is X safe", "how many active alerts", "weather in X", "how
many landslides in X") — **deliberately not an LLM**: no
ANTHROPIC_API_KEY (or any other LLM API key) exists anywhere in this
project, and adding one is an external-cost decision only the deploying
user can make. `app/services/assistant_service.py` matches a question
against a small set of real intents and answers entirely from real
database queries — every fact in every answer traces to a real row; an
unrecognized question returns what it can answer, never a guessed
response.

## Copy and status-field accuracy pass

Several user-facing labels and one backend field were stale from before
Phase 21+ added real derived zones, and were corrected for accuracy (not
just tone): `regions_with_demo_data`/`demo_regions` (an API field that
literally counted **all** zones, real and reference alike, mislabeled
"demo" from when that was still true) renamed to `total_zones`
everywhere (service, route, schema, frontend). The Dashboard's coverage
banner, the Analytics environmental-data notice, and the Data Sources
intro no longer claim "prototype"/"demo dataset" blanket coverage that
is no longer accurate — they now state the real, current zone-type
counts instead. System Status gained a real "Susceptibility Model" row
(`GET /data-status`'s new `susceptibility_model` field) alongside the
existing retired-classifier row, so the real Phase 22 model's status is
actually visible, not silently absent. **None of this touches the
underlying real/demo distinction in the data itself** — `source_type`,
`terrain_data_real`, and `risk_level: "UNKNOWN"` all still exist exactly
as before; only inaccurate or stale copy was corrected.
