# Test fixtures — TEST DATA, NOT real scientific data

Every file in this directory is synthetic, hand-crafted **test data** used
to exercise the Phase 9 ingestion pipeline (coordinate validation, date
parsing, column-alias mapping, duplicate detection, invalid-record
handling). None of it represents real landslide events, real rainfall
observations, or any other real-world measurement — do not register these
under `source_type=external_real` in any deployment, and do not cite them
as a real data source.

| File | Purpose |
| --- | --- |
| `landslides_test.csv` | Valid coordinates, invalid coordinates, a missing date, a duplicate `source_record_id`, and multiple column-name aliases (`Latitude`/`lat`, `lng`/`Longitude`) |
| `landslides_test.geojson` | Point geometries, one deliberately invalid/empty geometry, and a feature with missing properties |
| `rainfall_test.csv` | Valid observations, missing dates, a coverage gap, and one invalid (negative) rainfall value |
| `dem_test.tif` | A synthetic 10x10 GeoTIFF (EPSG:4326, ~30m pixels) with a known uniform north-south slope (elevation = 2000 + row*15m), used to verify `app/services/terrain_service.py`'s Horn's-method slope/aspect against an analytically-computable expected value (~26.57°) |
| `landcover_test.tif` | A synthetic 4x4 GeoTIFF with ESA WorldCover-style class codes (10/40/80), used to verify `app/services/landcover_service.py`'s point classification and scheme-mapping against known pixel values |
| `state_boundary_test.geojson` | Two synthetic polygon regions, used to verify `geospatial/india/boundary.py`'s point-in-polygon lookup |
| `susceptibility_verification_landslides.csv` | 5 landslide events placed at coordinate points that fall inside `dem_test.tif`'s and `landcover_test.tif`'s tiny real coverage windows (not otherwise overlapping), used to verify the Phase 20 susceptibility pipeline (`scripts/build_susceptibility_dataset.py`, `ml/susceptibility/`) end-to-end without any real DEM/rainfall/land-cover data |
| `susceptibility_verification_rainfall.csv` | Daily synthetic rainfall readings (Nov 2019 - Jan 2021) at the same coordinate used by the landslide fixture above, so `GET /rainfall/summary` has populated windows for every verification event's date |
