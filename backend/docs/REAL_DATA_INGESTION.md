# Real data ingestion (Phase 9)

This documents the architecture for safely ingesting real external
geospatial datasets. **As shipped, zero real datasets are configured or
registered** — everything here is architecture and tooling, not a claim
that real data currently exists in the system. Check `GET /data-status`'s
`real_data` block for the live truth at any time.

Two rules govern everything in this document:

> **REGISTERED DATA ≠ VALIDATED ML DATA.** Registering and ingesting a
> dataset here stores real records with real provenance — it does not
> mean that data has been vetted for, or used in, any ML training. The
> ML model (`backend/ml/`) still trains only on synthetic demo data; see
> Phase 9's own restriction against training a new model.

> **DATA COVERAGE ≠ RISK LEVEL.** A dataset being "available" or
> "processed" describes data completeness, not landslide risk. Ingesting
> a landslide inventory for one district does not raise or lower anyone's
> risk score — the rule-based/ML risk engines are unaffected by this
> pipeline entirely in Phase 9.

## Architecture

```text
backend/ingestion/
├── base.py            Connector status contract (not_configured / configured / credentials_required / download_failed)
├── checksum.py         SHA-256, streamed in chunks
├── validation.py        Safe multi-format date parsing (reuses geospatial.validators for coordinates)
├── storage.py           Batched inserts with progress + transaction boundaries
├── provenance.py         Registers a DataSource + records an IngestionRun
├── schemas.py            IngestionSummary / RejectedRecord dataclasses
├── connectors/
│   ├── manual.py          A user-supplied local file path
│   ├── nasa_landslide.py  Optional configured-URL download (timeout/retry/checksum/atomic move)
│   ├── imd_rainfall.py    Manual-path only (no automated bulk download assumed)
│   ├── dem.py             GeoTIFF metadata, requires optional 'rasterio'
│   ├── landcover.py       GeoTIFF metadata, requires optional 'rasterio'
│   └── boundaries.py      India/state/district boundary file status
└── processors/
    ├── landslides.py      CSV/GeoJSON -> validated, deduplicated LandslideEvent rows
    ├── rainfall.py         CSV -> validated, deduplicated RainfallObservation rows
    ├── terrain.py          DEM metadata extraction (no bulk elevation ingestion)
    ├── landcover.py        Land-cover metadata extraction
    └── boundaries.py       Validates a boundary file parses; reports feature count
```

Row-level parsing (CSV/GeoJSON column-alias detection) reuses Phase 3's
`geospatial/loaders.py` rather than duplicating it. Terrain/rainfall
"architecture" env vars from Phase 7 (`geospatial/terrain.py`,
`geospatial/rainfall.py`) are unchanged; Phase 9 adds the actual ingestion
CLI and storage on top of them.

## Database models (new)

- **`DataSource`** (`app/models/data_source.py`) — provenance for one
  dataset: name, category, provider, official URL, license, citation,
  coverage, access method, `local_file_name` (filename only — never a
  path), `file_size_bytes`, `checksum_sha256`, `configured`, `processed`,
  `last_status` (`registered → validated → processing → processed` or
  `failed`), `last_error`, `source_type` (`demo_synthetic` /
  `external_real` / `derived`).
- **`IngestionRun`** (`app/models/ingestion_run.py`) — one audit row per
  ingestion attempt: total/valid/invalid/inserted/duplicate counts,
  timestamps, status, error summary. `inserted` only ever reflects rows
  actually committed.
- **`RainfallObservation`** (`app/models/rainfall_observation.py`) — real
  historical rainfall records, distinct from Phase 6's live-weather
  `WeatherObservation`.
- **`LandslideEvent`** gained a `district` column (Phase 7 had `state`
  only) for boundary-derived enrichment (see below).

Migration: `alembic/versions/fda23df41b27_phase9_data_sources_rainfall_ingestion_.py`.
Applied and verified with `alembic check` → *"No new upgrade operations
detected."*

`MonitoringRegion`/`LandslideEvent`/`RainfallObservation` each carry a
PostGIS `geom` column (`POINT(longitude latitude)`, SRID 4326,
GIST-indexed) **only on PostgreSQL** — auto-synced from
`latitude`/`longitude` on insert/update. SQLite omits this column
entirely (GeoAlchemy2's `Geometry` type needs SpatiaLite, which local dev
doesn't install).

## Supported input formats

| Format | Status |
| --- | --- |
| CSV | Full support (stdlib `csv`, via `geospatial.loaders`) |
| GeoJSON | Full support (stdlib `json`) |
| JSON | Supported wherever GeoJSON is (same loader) |
| GeoPackage | Detected; requires the optional `fiona` package. Reading is not yet implemented — reports a clear "not yet implemented" reason rather than faking support |
| GeoTIFF | Metadata extraction (CRS, resolution, bounding box, nodata, dimensions) requires the optional `rasterio` package, which is **not** a base dependency. Without it, DEM/land-cover ingestion reports `available: false` with the exact reason — never a guess |

## Manual dataset registration & ingestion

```bash
cd backend
python scripts/ingest_dataset.py \
    --category historical_landslide \
    --path data/raw/external/landslides.csv \
    --name "Example Landslide Inventory" \
    --provider "Example Geological Survey" \
    --source-url "https://official-source.example" \
    --license "CC-BY-4.0" \
    --citation "Example et al., 2024" \
    --geographic-coverage "Sikkim, West Bengal" \
    --temporal-coverage "2015-2023" \
    --limitations "Point locations only; no severity classification"
```

This: verifies the file exists → inspects it (columns/row count) →
computes a SHA-256 checksum and file size → registers a `DataSource` row
(`configured=true` only now, since the file was actually found) →
validates and processes rows (for `historical_landslide`/`rainfall`) or
extracts metadata (for `terrain`/`vegetation`/`boundary`) → records an
`IngestionRun` → prints a summary. **It never modifies the original
file** and never marks a dataset `processed=true` unless processing
genuinely succeeded.

Lighter-weight, metadata-only registration (no ingestion) is still
available via `scripts/register_data_source.py`, kept from Phase 7 for
cases where you want provenance recorded before deciding to ingest.

### Listing and inspecting

```bash
python scripts/list_data_sources.py
python scripts/list_data_sources.py --category rainfall
python scripts/inspect_dataset.py path/to/data.csv   # read-only, from Phase 3 — reused, not duplicated
```

## Column aliasing (flexible mapping)

Real-world exports vary in header naming. `geospatial/loaders.py`'s
alias table now **merges** (rather than replaces) per-field alias lists,
so ingestion processors can add dataset-specific aliases without losing
the defaults. Landslide ingestion recognizes `latitude`/`lat`/`Latitude`,
`longitude`/`lon`/`lng`/`Longitude`, `date`/`event_date`/`eventDate`,
`state`/`State`, `district`/`District`, `severity`, `event_type`, and a
`source_record_id` alias (`record_id`, `id`, `ID`, `OBJECTID`, `fid`).

## Validation rules

- Coordinates: latitude −90..90, longitude −180..180 (reused from
  `geospatial/validators.py`) — a row failing this is rejected, not
  dropped silently; its row index and reason are kept.
- Dates: parsed via `ingestion/validation.parse_date_safely` (ISO +
  common formats). Unparseable or missing dates become `NULL` — never
  guessed.
- Rainfall: negative values are rejected.
- **India-boundary-aware, never India-restrictive**: valid global
  coordinates are never rejected just because no India boundary is
  configured. A configured boundary is only ever used to *enrich*
  `state`/`district` when the source data didn't already supply them.

## Duplicate detection

Conservative and per-source: prefers an explicit `source_record_id` when
the dataset provides one; otherwise falls back to a
`(latitude, longitude, date)` composite key. **Coordinates alone are
never a unique key** (different events can share a location). Detection
checks both rows already in the database for that `source_id` and rows
already seen earlier in the same file, so re-running an ingestion is
idempotent — verified by ingesting the same file twice and confirming
zero new rows the second time.

## Boundary-based state/district enrichment

`geospatial/india/boundary.py` supports three independent, optional
GeoJSON boundaries — `BHUSURAKSHA_INDIA_BOUNDARY_PATH`,
`BHUSURAKSHA_STATE_BOUNDARY_PATH`, `BHUSURAKSHA_DISTRICT_BOUNDARY_PATH` —
and does real point-in-polygon lookups (pure-Python ray casting, no
GDAL/shapely dependency) once a boundary is actually configured. If a
landslide record's source data doesn't supply `state`/`district`, and a
boundary is configured and available, the actual polygon match fills
them in; otherwise they stay `NULL`. Verified with a test fixture
polygon and real Darjeeling/Guwahati-area coordinates.

## Large dataset safety

- `ingestion/checksum.py` streams files in 1 MiB chunks — never loads
  a whole file into memory just to hash it.
- `ingestion/storage.batched_insert` commits every 500 rows by default
  (configurable via `--batch-size`), so one failure partway through a
  huge file doesn't roll back everything already safely stored, and
  memory stays bounded regardless of dataset size.
- Every processor returns per-row rejection reasons (`IngestionSummary.rejected`)
  instead of failing the whole dataset for one bad record.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `BHUSURAKSHA_NASA_LANDSLIDE_URL` | Optional configured download URL for a global landslide inventory |
| `BHUSURAKSHA_IMD_RAINFALL_PATH` | Manual local path to a rainfall dataset |
| `BHUSURAKSHA_DEM_PATH` | Manual local path to a DEM GeoTIFF |
| `BHUSURAKSHA_LANDCOVER_PATH` | Manual local path to a land-cover GeoTIFF |
| `BHUSURAKSHA_INDIA_BOUNDARY_PATH` / `BHUSURAKSHA_STATE_BOUNDARY_PATH` / `BHUSURAKSHA_DISTRICT_BOUNDARY_PATH` | Optional real boundary GeoJSON files |

None are required. The application starts and works fully with zero of
these set — verified by starting the full Docker Compose stack with no
real datasets configured at all.

## Safe download architecture (NASA connector)

```text
temporary file → download complete → validate (non-empty) → checksum → atomic move into place
```

- Timeout (30s) and up to 3 retries.
- Never overwrites an existing destination file silently.
- A 401/403 response is reported as `credentials_required` with a
  pointer back to this document — BHUSURAKSHA never attempts to bypass
  authentication.
- No URL is hardcoded anywhere; if `BHUSURAKSHA_NASA_LANDSLIDE_URL` is
  unset, the connector reports `not_configured` and nothing happens.

Tested against a local HTTP server: successful download + checksum +
atomic move (byte-identical to source), refusal to overwrite an existing
file, and a simulated 401 correctly reported as `credentials_required`
with no partial file left behind.

## Adding a new source connector

1. Add `ingestion/connectors/<name>.py` implementing `status()` (and
   `download()` if applicable) per `ingestion/base.BaseConnector`.
2. If it produces row-level records, add `ingestion/processors/<name>.py`
   following the pattern in `landslides.py`/`rainfall.py`: load via
   `geospatial.loaders`, validate, deduplicate conservatively, batch
   insert via `ingestion.storage.batched_insert`.
3. Wire it into `scripts/ingest_dataset.py`'s category dispatch.
4. Document the new environment variable and category here.

## Docker

Real datasets are **never** baked into the Docker image. `docker-compose.yml`
already mounts `./backend/data/raw/external` into the `backend` service at
`/app/data/raw/external`, so a file placed there on the host is visible to
the running container without a rebuild:

```bash
cp your_dataset.csv backend/data/raw/external/
docker compose exec backend python scripts/ingest_dataset.py \
    --category historical_landslide \
    --path data/raw/external/your_dataset.csv \
    --name "Your Dataset Name"
```

For a category that reads its path from an environment variable (DEM,
land cover) instead, set it in `.env` / the `backend` service's
`environment:` block, e.g. `BHUSURAKSHA_DEM_PATH: /app/data/raw/external/my_dem.tif`.

The application starts and works with **zero** real datasets configured
— verified by running the full stack (`docker compose up --build`, all 3
services healthy, PostGIS 3.4 confirmed via `GET /health`) with no real
datasets present, then separately ingesting `tests/fixtures/landslides_test.csv`
(via `docker compose exec backend ...`, using the mount above) end-to-end
and confirming correct results through `GET /landslides`, the PostGIS
`geom` column, and the frontend nginx proxy, before removing the test
data again.

## Test fixtures

`backend/tests/fixtures/` contains small, clearly-labeled **TEST DATA**
(not real scientific data) used to verify: valid/invalid coordinates,
missing dates, duplicate `source_record_id`s, multiple column aliases
(CSV), Point geometries / invalid geometry / missing properties
(GeoJSON), and valid/missing-date/gap/invalid-value rainfall readings.
See `tests/fixtures/README.md`.

## Known limitations

- GeoPackage reading and DEM/land-cover raster metadata require optional
  dependencies (`fiona`, `rasterio`) not installed by default — this is
  deliberate (avoiding a heavy GIS dependency stack per this phase's
  scope), not an oversight.
- Point-in-polygon boundary lookups only support `Polygon`/`MultiPolygon`
  GeoJSON — no GeoPackage boundary support yet.
- `rainfall_24h`/`7d`/`30d` accumulation windows described conceptually
  in Phase 7's `geospatial/rainfall.py` are not computed from ingested
  `RainfallObservation` rows in this phase — only raw observations are
  stored.

## Spatial query API & map visualization (Phase 10)

Three new read-only endpoints in `app/routes/landslides.py` (backed by
`app/services/spatial_service.py`), all bounded — none ever return an
unbounded inventory:

| Endpoint | Purpose | Cap |
| --- | --- | --- |
| `GET /landslides/nearby?lat=&lon=&radius_km=` | Radius search around a point | `radius_km` ≤ 500, results ≤ 200 |
| `GET /landslides/map?min_lat=&min_lon=&max_lat=&max_lon=` | Map-viewport bounding box | results ≤ 2000 (`truncated: true` when more match) |
| `GET /data-sources/{id}/quality` | Record-completeness ("Data Completeness", never "accuracy") | — |

**PostGIS vs SQLite — never pretends SQLite has PostGIS:**
- `/landslides/map` (a lat/lon bounding box) is exact on both — PostGIS
  uses `ST_Intersects`/`ST_MakeEnvelope`, SQLite uses a plain `BETWEEN`
  filter. Both are precise for a rectangular bbox; no geodesic math is
  involved either way. `spatial_backend` in the response reads `"postgis"`
  or `"sqlite_exact"`.
- `/landslides/nearby` (a geodesic radius) genuinely needs PostGIS for
  index-accelerated accuracy: `ST_DWithin`/`ST_Distance` cast to
  `geography`. On SQLite, a degrees-per-km bounding-box pre-filter narrows
  candidates (capped at 5000), then an exact Python haversine computes
  real distance and applies the radius — `spatial_backend` reads
  `"sqlite_approximate"` so callers always know which path served the
  request.

Verified against a real PostgreSQL 16 + PostGIS 3.4 container: `alembic
upgrade head` → `alembic check` (*"No new upgrade operations detected"* —
no schema changes were needed; the `idx_landslide_events_geom` GIST index
already existed from Phase 9's initial migration) → ingested a test
fixture → confirmed via direct SQL that `geom` is `POINT(longitude
latitude)`, SRID 4326, `ST_X(geom) = longitude`, `ST_Y(geom) = latitude`
(never swapped) → `/landslides/nearby` and `/landslides/map` both
returned `spatial_backend: "postgis"` with geometrically correct results.

**Frontend (Risk Map):** a "Historical Landslides" map layer
(`components/map/HistoricalEventsLayer.jsx`) queries `/landslides/map`
using the map's current viewport bounds (via `MapViewportWatcher.jsx`,
re-querying on pan/zoom `moveend`/`zoomend` — never the whole table) and
renders clustered markers using `leaflet.markercluster` (used
imperatively via `L.markerClusterGroup()`, the same way the existing
`MapController` already drives Leaflet directly — not a React wrapper
package, to avoid an untested React-19 compatibility risk). Markers are a
neutral slate diamond — deliberately not circular or risk-colored, so a
past observation can never be mistaken for a current risk marker.
Clicking one opens `EventDetailModal.jsx` (event date, state, district,
type, severity, source dataset, coordinates — missing fields read "Not
available", never fabricated or shown as "Unknown"). Supports filtering
by state, data source, and date range. Analytics gained an "Events by
Source" chart alongside the existing "Events by State"/"Events over
Time"; Data Sources' detail modal gained a "Data Completeness" section
(coordinates/date/state/district/type/severity population rates) —
explicitly labeled completeness, never accuracy.

All of the above was verified with zero real datasets registered (every
empty state — map layer, Analytics, Data Sources — reads honestly, e.g.
"No historical landslide data available") and, separately, with the
`tests/fixtures/landslides_test.csv` **test fixture** temporarily
ingested and then removed again — this fixture is not real data and the
application ships with zero real datasets registered.
