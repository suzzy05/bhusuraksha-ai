# BHUSURAKSHA AI — Backend

FastAPI backend for the landslide early warning and risk monitoring platform.

## Installation

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS / Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the server

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

On first run, the app automatically creates `bhusuraksha.db` (SQLite), seeds
seven demo zones (Darjeeling, Gangtok, Kalimpong, Shillong, Guwahati, Aizawl,
Itanagar), and generates alerts for zones at HIGH or CRITICAL risk.

## Configuration

Copy `.env.example` to `.env` to override the database location:

```bash
cp .env.example .env
```

## API Endpoints

| Method | Path             | Description                                  |
| ------ | ---------------- | --------------------------------------------- |
| GET    | `/health`        | Health check                                  |
| GET    | `/zones`         | List all zones with risk scores               |
| GET    | `/zones/{id}`    | Zone detail with environment + risk factors   |
| POST   | `/predict-risk`  | Calculate risk from arbitrary input values    |
| GET    | `/alerts`        | List active alerts                            |
| GET    | `/data-status`   | Which data sources (demo/external/processed/live weather) are wired up |
| GET    | `/weather/{zone_id}` | Live weather for a zone's coordinates (no zone data changed) |
| POST   | `/weather/{zone_id}/refresh` | Fetch live weather, update the zone, recompute risk |
| POST   | `/weather/refresh-all` | Run the above for every zone; per-zone failures don't abort the batch |
| GET    | `/weather/{zone_id}/history` | Recent stored weather observations, newest first |
| GET    | `/landslides`    | Paginated historical landslide events (filters: `state`, `source_id`, `start_date`, `end_date`) |
| GET    | `/landslides/{id}` | Single landslide event |
| GET    | `/regions`       | Monitoring regions (filters: `state`, `source_type`) |
| GET    | `/regions/{id}`  | Single monitoring region |
| GET    | `/india/summary` | Pan-India monitoring coverage counts (never claims national coverage) |
| GET    | `/data-sources`  | Registered real/derived dataset provenance (filter: `category`) |
| GET    | `/data-sources/{id}` | Full provenance detail for one dataset |
| GET    | `/data-sources/{id}/status` | Ingestion status + run history for one dataset |

## Risk engine

`app/services/risk_service.py` implements a deterministic, rule-based risk
score (0–100) from rainfall, slope, vegetation cover, historical landslide
history, and humidity. It is isolated behind a single `calculate_risk()`
function, and remains the guaranteed fallback used whenever the ML model
below is unavailable.

## Machine learning (Phase 2)

See [docs/ML_LIMITATIONS.md](docs/ML_LIMITATIONS.md) for the full,
current picture — no real-world-validated model exists yet.

`POST /predict-risk` tries a trained `RandomForestClassifier` first and
transparently falls back to the rule-based engine if no model is available
— the endpoint never crashes due to a missing model. The response's
`prediction_source` field tells you which path was used:

- `"machine_learning"` — the model predicted the risk level. The response
  also includes `class_probabilities` (per-class confidence) and
  `feature_importance` (global RandomForest feature importances — **not**
  specific to this one prediction).
- `"rule_based_fallback"` — the model file was missing or failed to load,
  so the deterministic engine answered instead. `class_probabilities` and
  `feature_importance` are `null` in this case.

`risk_factors` (the rule-based, per-prediction explanation) is always
included regardless of `prediction_source`.

### Training the model

Demo synthetic training data lives at
`data/raw/demo/landslide_training_data.csv` — see
[`data/raw/demo/README.md`](data/raw/demo/README.md). **This is
hand-crafted demo data for prototyping the pipeline, not a real-world
landslide dataset**; a later phase is expected to swap in real
environmental/landslide data. Because the synthetic classes are cleanly
separated by construction, the model's evaluation accuracy is very high —
that reflects how easy this demo dataset is, not real-world performance.

Regenerate the dataset (fixed seed, reproducible):

```bash
python data/generate_dataset.py
```

Train the model and save artifacts to `ml/artifacts/`:

```bash
python -m ml.train_model
```

This prints a training summary (dataset/train/test row counts, accuracy,
classification report, confusion matrix — all real, calculated metrics) and
writes:

- `ml/artifacts/landslide_model.joblib` — the trained model
- `ml/artifacts/model_metadata.json` — feature names, model type, training
  timestamp, and metrics

If `landslide_model.joblib` is missing or fails to load, `/predict-risk`
automatically uses the rule-based fallback — no code changes needed.

## Phase 3 — real data pipeline

Phase 3 adds a modular pipeline (`geospatial/`) for ingesting real,
external geospatial datasets (historical landslide inventories, rainfall
records, DEM/vegetation exports) — it does **not** replace anything from
Phases 1–2:

1. The ML model in `ml/artifacts/` still trains only on the synthetic demo
   dataset; Phase 3 does not retrain it automatically.
2. Nothing here claims scientific prediction accuracy — see
   [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for exactly which real
   sources are (not yet) integrated and why.
3. External datasets are loaded, validated, and normalized independently
   of the demo ML dataset — the two are never mixed silently. Every
   processed record carries a `source_type` of `demo_synthetic` or
   `external_real` (see [`data/README.md`](data/README.md)).
4. Dataset provenance (source name, file type, processing timestamp,
   limitations) is preserved in `data/processed/processed_landslide_metadata.json`.
5. Any feature a source dataset doesn't provide is left `None` in the
   processed output — nothing is invented to fill a gap.
6. Real ML retraining only happens once a real, labeled dataset is
   actually prepared; `risk_level` is left unset for every real-world
   record in the meantime.

### Dataset inspection (read-only)

```bash
python scripts/inspect_dataset.py path/to/data.csv
python scripts/inspect_dataset.py path/to/data.geojson
```

Prints row count, columns, detected latitude/longitude/date columns,
missing-value counts, sample rows, and a geographic bounding box. Never
modifies the file.

### Running the pipeline

```bash
python scripts/run_geospatial_pipeline.py --landslide path/to/data.csv
python scripts/run_geospatial_pipeline.py --landslide path/to/data.csv --rainfall path/to/rainfall.csv
```

Works with just one dataset, or both. Loads → validates → normalizes onto
the common `GeoRiskRecord` schema (`geospatial/schemas.py`) → scores each
record's data completeness (`data_quality_score`, 0–100 — **completeness,
not risk**) → writes:

- `data/processed/processed_landslide_records.csv`
- `data/processed/processed_landslide_metadata.json`

Invalid records (bad coordinates, out-of-range values, duplicates) are
never silently dropped — they're counted and the reason is recorded.

### Configuring external datasets without the CLI

Optionally point the pipeline at datasets via environment variables
instead of CLI flags: `BHUSURAKSHA_LANDSLIDE_DATA_PATH`,
`BHUSURAKSHA_RAINFALL_DATA_PATH`, `BHUSURAKSHA_DEM_DATA_PATH`,
`BHUSURAKSHA_VEGETATION_DATA_PATH` (see `geospatial/config.py`). None of
these are required — if unset, `GET /data-status` reports them as
`"configured": false` and nothing crashes.

## Phase 6 — live weather integration

`app/services/weather_service.py` fetches current temperature, humidity,
and a real 24h rainfall sum (computed from the provider's hourly
precipitation series) from [Open-Meteo](https://open-meteo.com) — free,
no API key. The provider is abstracted behind `get_current_weather()` so a
different backend can be swapped in later via the `WEATHER_PROVIDER` env
var.

- `GET /weather/{zone_id}` fetches live weather without changing anything.
- `POST /weather/{zone_id}/refresh` updates only the zone fields the
  provider actually returned (existing values are kept for anything
  unavailable), stores a `WeatherObservation` row, then recomputes risk via
  `app/services/risk_update_service.py` (ML-first, rule-based fallback —
  same policy as `/predict-risk`, no retraining) and reconciles alerts:
  at most one active alert per zone, matching its current severity;
  superseded/resolved alerts are marked `is_active=False`, never deleted.
- `POST /weather/refresh-all` runs the above for every zone. Zones are
  processed independently, so one zone's provider failure doesn't abort
  the batch.
- `GET /weather/{zone_id}/history` returns real stored observations,
  newest first — empty until a refresh has actually happened.
- If the weather provider is unreachable, `available: false` is returned
  and stored zone values are left untouched — never zeroed or nulled out.

**Scientific limitation** (see [docs/WEATHER_LIMITATIONS.md](docs/WEATHER_LIMITATIONS.md)
for the full explanation): current weather conditions alone do not
constitute a validated landslide early-warning model. Multi-day rainfall
accumulation, soil/geology data, a real DEM, current vegetation, and a
validated landslide inventory all matter too — this integration improves
situational awareness, it does not replace them.

## Phase 7 — pan-India real data foundation

Phase 7 adds the *architecture* for scaling coverage across India — it
does **not** claim the system currently monitors all of India. The
platform's actual position: "pan-India landslide intelligence with
detailed analysis where appropriate data coverage exists."

- **`MonitoringRegion`** (`app/models/monitoring_region.py`) — a scalable
  geographic entity (`state`/`district`/`point`/`grid_cell`/`custom_region`).
  Deliberately **not** bulk-populated with a synthetic India-wide grid; it
  stays empty until backed by an actual registered dataset. `coverage_score`
  is data completeness, never risk.
- **`LandslideEvent`** (`app/models/landslide_event.py`) — a historical
  landslide record. Any field a real dataset doesn't supply
  (`event_date`, `event_type`, `severity`, `state`) stays `NULL`, never
  fabricated. `GET /landslides` is paginated (`page`, `page_size` capped
  at 200) with `state`/`source_id`/`start_date`/`end_date` filters;
  `GET /landslides/{id}` fetches one.
- Existing Phase 1 seeded zones keep working unchanged and are explicitly
  tagged `source_type="demo_seed"` on the `Zone` model, distinct from
  `external_real` and `derived` — demo and real data are never mixed
  silently.
- **`geospatial/source_registry.py`** — provenance registry for external
  datasets (source URL, license, coverage, limitations). `configured` is
  only ever true once a file has actually been found and inspected, never
  from documentation alone. Register one with:

  ```bash
  python scripts/register_data_source.py \
      --name "Landslide Dataset" --category historical_landslide \
      --path data/raw/external/landslides.csv \
      --source-url "OFFICIAL_URL"
  ```

  This only records metadata — it never downloads data, modifies the
  source file, or loads rows into the database.
- **`geospatial/terrain.py`**, **`geospatial/rainfall.py`** — documented
  extension points for a real DEM and a real historical rainfall dataset
  (distinct from Phase 6's live-weather-only integration). Both report
  `available: false` with a clear reason rather than estimating a value.
- **`geospatial/india/`** — India administrative boundary support via
  `BHUSURAKSHA_INDIA_BOUNDARY_PATH`; unset by default, and the app works
  fully without it ("India boundary dataset not configured.").
- **`GET /india/summary`** and the `india_monitoring` block of
  `GET /data-status` report real counts (monitoring regions, real-data
  regions, demo regions, historical events) and a conservative
  `coverage_status` (`prototype` → `partial_real_data` →
  `regional_real_data` → `expanded_real_data`) that only advances as real
  data actually accumulates.
- **`GET /regions`** / **`GET /regions/{id}`** — list/fetch `MonitoringRegion`
  rows (filters: `state`, `source_type`). Empty by default, same as
  `LandslideEvent` — never auto-populated with a synthetic grid.

## Phase 8 — PostgreSQL + PostGIS + Docker

`DATABASE_URL` controls everything: unset or `sqlite:///...` keeps today's
zero-setup SQLite dev workflow (`create_all()` on startup, unchanged);
`postgresql+psycopg://...` switches to PostgreSQL, where schema is managed
by **Alembic migrations** instead (`alembic upgrade head` — see
`alembic/`). `MonitoringRegion`/`LandslideEvent` get a PostGIS `geom`
column (SRID 4326, GIST-indexed, auto-synced from `latitude`/`longitude`)
**only** when actually running on PostgreSQL — SQLite models omit it
entirely, since GeoAlchemy2's `Geometry` type requires SpatiaLite.

`GET /health` now reports `database: {connected, type}` and, on
PostgreSQL, `postgis: {available, version}` — never a connection string or
raw exception text.

New scripts: `scripts/seed_database.py` (idempotent explicit seeding) and
`scripts/migrate_sqlite_to_postgres.py` (safe, manual, `--confirm`-gated
SQLite → PostgreSQL data migration with count validation). Full Docker
Compose setup, environment variables, and troubleshooting:
[../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

## Phase 9 — real data ingestion platform

`backend/ingestion/` adds CLI-driven ingestion of real external datasets:
checksummed provenance (`DataSource`), an audit trail per run
(`IngestionRun`), and processors for historical landslides (CSV/GeoJSON →
`LandslideEvent`) and rainfall (CSV → `RainfallObservation`), plus
metadata-only registration for terrain/land-cover/boundary files.
Duplicate detection is conservative (`source_record_id`, or a
`(lat, lon, date)` composite — never coordinates alone) and idempotent —
re-running the same file inserts zero new rows. As shipped, **zero real
datasets are registered**; everything reports honestly via
`GET /data-status`'s `real_data` block and `GET /data-sources`.

```bash
python scripts/ingest_dataset.py --category historical_landslide --path data/raw/external/landslides.csv --name "My Dataset"
python scripts/list_data_sources.py
```

Full architecture, supported formats, environment variables, and the
`REGISTERED DATA ≠ VALIDATED ML DATA` / `DATA COVERAGE ≠ RISK LEVEL`
principles: [docs/REAL_DATA_INGESTION.md](docs/REAL_DATA_INGESTION.md).
