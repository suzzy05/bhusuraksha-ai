# Data sources

**Status: five real-world datasets are registered and ingested** — a
global historical landslide inventory (section A), plus real rainfall,
DEM, and land-cover coverage for a two-state pilot area (sections B/C/E) —
**India-wide coverage for rainfall/DEM/land-cover does not exist**, only
the Uttarakhand + Himachal Pradesh pilot. Everything below documents
the *categories* of real data BHUSURAKSHA AI's geospatial pipeline
([`../geospatial/`](../geospatial/)) is built to accept, and the metadata
every real source is recorded with. Check `GET /data-status` at any time
for the live, authoritative counts — this file is documentation, not the
source of truth.

Source URLs are intentionally omitted rather than guessed. When a real
dataset is provided, fill in its actual metadata block below (or in the
metadata JSON the pipeline generates) — do not invent a source, license, or
coverage claim for it.

## Source metadata fields

Every real source, once integrated, should be documented with:

| Field                  | Meaning                                              |
| ----------------------- | ----------------------------------------------------- |
| `source_name`          | Short identifier used in code/metadata                |
| `source_url`           | Where the dataset came from (only if actually known)  |
| `license`              | Usage terms/license of the dataset                    |
| `access_date`          | When the dataset was obtained                         |
| `geographic_coverage`  | Region(s) the dataset actually covers                 |
| `temporal_coverage`    | Date range the dataset actually covers                |
| `limitations`          | Known gaps, resolution limits, biases, etc.           |

---

## A. Historical landslide inventory

**Purpose:** locations and/or dates of historical landslide events — the
closest thing to ground-truth labels this project could eventually train
on.

**Expected fields (where available):**

- `latitude`
- `longitude`
- `date`
- `event_type`
- `severity`

**Metadata (registered `source_id: nasa_global_landslide_catalog_export`):**

| Field | Value |
| --- | --- |
| `source_name` | NASA Global Landslide Catalog Export |
| `source_url` | https://data.nasa.gov/dataset/global-landslide-catalog-export |
| `provider` | NASA Goddard Space Flight Center |
| `license` | Public domain / U.S. Government work (cite Kirschbaum et al. 2010, 2015) |
| `access_date` | 2026-08-31 |
| `geographic_coverage` | Global (news-media-reported rainfall-triggered landslides, ~70+ countries) |
| `temporal_coverage` | 1970-01-01 to 2016-03-07 (export snapshot; not actively updated at this URL — see COOLR for newer data) |
| `limitations` | Media/news-derived, not systematic field surveys; reporting bias toward populated/English-media-covered areas; point locations only; ~14.8% of rows missing country/admin-division metadata |
| `rows ingested` | 11,033 (0 rejected, 0 duplicates on first ingestion) |

Ingested via `scripts/ingest_dataset.py --category historical_landslide`;
verify current row counts with `GET /data-status` (`real_data.landslide_events`)
or `python scripts/list_data_sources.py`. **Registered ≠ ML-validated** — see
the "ML integration preparation" note below; the Phase 2 synthetic model is
unaffected.

**Integration:** [`geospatial.loaders.load_landslide_inventory`](../geospatial/loaders.py)

---

## B. Rainfall data

**Purpose:** precipitation readings used to derive `rainfall_24h` /
`rainfall_7d` features.

**Potential fields:**

- `date`
- `latitude`
- `longitude`
- `rainfall`

**Metadata (registered `source_id: imd_gridded_rainfall_0.25deg_(pilot_points)`):**

| Field | Value |
| --- | --- |
| `source_name` | IMD Gridded Rainfall 0.25deg (pilot points) |
| `source_url` | https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html |
| `provider` | India Meteorological Department |
| `license` | Public (IMD data-access disclaimer applies; no accuracy warranty) |
| `geographic_coverage` | Uttarakhand + Himachal Pradesh pilot area — point extractions only, NOT the full national grid |
| `temporal_coverage` | 2007-2017 (real event/negative dates in the pilot) |
| `limitations` | Gridded (0.25deg) daily estimate interpolated from IMD's station network, not individual gauge readings; extracted only at the exact 1,848 pilot event/negative coordinates and their real lookback windows |
| `rows ingested` | 57,854 (162 legitimate duplicates from overlapping lookback windows) |

Extracted via `scripts/extract_imd_rainfall.py` (downloads IMD's own public
per-year NetCDF form, no login), registered via `scripts/ingest_dataset.py
--category rainfall`.

**Integration:** [`geospatial.loaders.load_rainfall_dataset`](../geospatial/loaders.py),
[`geospatial.feature_engineering.calculate_rainfall_windows`](../geospatial/feature_engineering.py),
[`app/services/rainfall_service.py`](../app/services/rainfall_service.py) (real accumulation windows)

---

## C. Digital Elevation Model (DEM)

**Purpose:** terrain elevation, the basis for slope calculation.

**Expected output:** `elevation`

**Metadata (registered `source_id: copernicus_dem_glo-30_(pilot_mosaic)`):**

| Field | Value |
| --- | --- |
| `source_name` | Copernicus DEM GLO-30 (pilot mosaic) |
| `source_url` | https://registry.opendata.aws/copernicus-dem/ |
| `provider` | European Space Agency / Copernicus Programme |
| `license` | Copernicus DEM open license |
| `geographic_coverage` | Uttarakhand + Himachal Pradesh pilot bbox (28.4-33.3N, 75.4-81.1E) |
| `limitations` | Mosaic of 32/42 1x1-degree tiles — 10 failed on transient DNS errors and were not force-retried; those areas honestly report `terrain_available: false`, never interpolated |

Served live via [`app/services/terrain_service.py`](../app/services/terrain_service.py)
(Horn's-method slope/aspect, `GET /terrain/features`) once
`BHUSURAKSHA_DEM_DATA_PATH` points at the mosaic — windowed single/3×3-pixel
reads (fixed in Phase 22; the original per-call full-band read was a real
performance bug against a real large mosaic).

---

## D. Terrain slope

**Purpose:** steepness, derived from elevation data.

**Expected output:** `slope_degrees`

**Metadata:** *not yet supplied.*

**Integration:** [`geospatial.feature_engineering.calculate_slope`](../geospatial/feature_engineering.py)
is a documented extension point — it currently returns `None` (or raises
`NotImplementedError` if a DEM is actually referenced) rather than
pretending to compute a real DEM-derived slope. If a source dataset already
provides a `slope` column, it passes through unchanged.

---

## E. Vegetation / land cover

**Purpose:** vegetation density or land-cover classification.

**Expected output:** a vegetation index (0.0–1.0) or land-cover class.

**Metadata (registered `source_id: esa_worldcover_10m_2021_v200_(pilot_mosaic)`):**

| Field | Value |
| --- | --- |
| `source_name` | ESA WorldCover 10m 2021 v200 (pilot mosaic) |
| `source_url` | https://registry.opendata.aws/esa-worldcover/ |
| `provider` | European Space Agency |
| `license` | CC-BY-4.0 |
| `geographic_coverage` | Uttarakhand + Himachal Pradesh pilot bbox (28.4-33.3N, 75.4-81.1E) |
| `temporal_coverage` | 2021 |

Full 9/9-tile mosaic. Served live via
[`app/services/landcover_service.py`](../app/services/landcover_service.py)
(`GET /landcover`) — raw class codes mapped to normalized categories via
the real, published ESA WorldCover legend
([`geospatial/landcover_schemes.py`](../geospatial/landcover_schemes.py)).

**Integration:** [`geospatial.feature_engineering.normalize_vegetation`](../geospatial/feature_engineering.py)
rescales a supported input scale (already 0–1, a 0–100 percentage, or raw
NDVI) onto 0.0–1.0. It does not invent a vegetation value where none is
present in the source data.

---

## ML integration preparation

Superseded by Phase 20/22 for the pilot area: `app/services/
feature_engineering_service.build_feature_vector(lat, lon, as_of)` now does
the real geospatial/temporal join this section originally described as "not
implemented" — combining rainfall, terrain, land cover, and historical-
density for one real coordinate/time. `scripts/build_susceptibility_dataset.py`
applies this to every real event + generated negative to build a real
training set, and `ml/susceptibility/` trains on it — see
[ML_LIMITATIONS.md](ML_LIMITATIONS.md) for the real result and its limits.
The Phase 2 demo model this section originally referred to was retired in
Phase 19; `risk_level` is still never fabricated for any `LandslideEvent`
row (there's no column for it at all), and the Phase 21 `label` column on
the susceptibility dataset is a real presence/pseudo-absence signal, not a
risk level.
