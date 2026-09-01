"""Phase 24 — fills real slope/elevation for every derived Zone that
doesn't have real terrain yet, using TARGETED single-tile downloads (only
the exact 1x1-degree Copernicus DEM tile each zone's real coordinate falls
in — not a full bounding-box mosaic, which would re-download most of
India's land area just to reach a few dozen scattered points).

Real source: Copernicus DEM GLO-30 (AWS Open Data Registry), the same
product Phase 22's pilot mosaic used — just fetched per-tile here instead
of mosaicked, since these zones are geographically scattered across India,
not one contiguous study area.

For each zone: downloads (or reuses a cached) tile covering its exact
coordinate, reads a real 3x3-pixel neighborhood there via the same Horn's-
method slope/aspect code `app/services/terrain_service.py` uses for live
serving (imported directly, not reimplemented), and sets
`Zone.slope`/`Zone.elevation`/`Zone.terrain_data_real=True`. A zone whose
tile genuinely doesn't exist (ocean edge, transient download failure) is
left honestly untouched — never a fabricated value.

Does NOT touch risk_score/risk_level — run `POST /weather/refresh-all`
afterward to let the normal, already-existing risk-update flow compute a
real score now that real terrain exists (same mechanism Phase 23 already
verified for the original 4 pilot-area zones).

Usage:
    python scripts/enrich_zones_with_real_terrain.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.zone import Zone  # noqa: E402
from app.services.terrain_service import METERS_PER_DEGREE_LAT, _horn_slope_aspect  # noqa: E402
from scripts.prepare_pilot_rasters import dem_url, download  # noqa: E402

TILE_DIR = Path("data/raw/external/national_points/dem_tiles")


def _real_terrain_from_tile(tile_path: Path, lat: float, lon: float):
    import rasterio
    from rasterio.windows import Window

    with rasterio.open(tile_path) as dataset:
        row, col = dataset.index(lon, lat)
        if not (0 <= row < dataset.height and 0 <= col < dataset.width):
            return None

        has_neighborhood = 1 <= row <= dataset.height - 2 and 1 <= col <= dataset.width - 2
        if has_neighborhood:
            neighborhood = dataset.read(1, window=Window(col - 1, row - 1, 3, 3))
            elevation = float(neighborhood[1, 1])
        else:
            pixel = dataset.read(1, window=Window(col, row, 1, 1))
            elevation = float(pixel[0, 0])

        if dataset.nodata is not None and elevation == dataset.nodata:
            return None

        cellsize_x, cellsize_y = dataset.res
        if dataset.crs and dataset.crs.is_geographic:
            meters_per_degree_lon = METERS_PER_DEGREE_LAT * math.cos(math.radians(lat))
            cellsize_x = cellsize_x * meters_per_degree_lon
            cellsize_y = cellsize_y * METERS_PER_DEGREE_LAT

        if not has_neighborhood:
            return elevation, None
        slope_degrees, _aspect = _horn_slope_aspect(neighborhood, cellsize_x, cellsize_y)
        return elevation, slope_degrees


def main():
    db = SessionLocal()
    try:
        zones = db.query(Zone).filter(Zone.source_type == "derived", Zone.terrain_data_real.is_(False)).all()
        print(f"Zones needing real terrain: {len(zones)}")

        tile_cache: dict = {}
        enriched = 0
        no_coverage = 0
        for zone in zones:
            tile_id = (math.floor(zone.latitude), math.floor(zone.longitude))
            if tile_id not in tile_cache:
                url = dem_url(*tile_id)
                dest = TILE_DIR / Path(url).name
                ok = download(url, dest)
                tile_cache[tile_id] = dest if ok else None

            tile_path = tile_cache[tile_id]
            if tile_path is None:
                no_coverage += 1
                print(f"  {zone.name}: tile unavailable, left as-is")
                continue

            result = _real_terrain_from_tile(tile_path, zone.latitude, zone.longitude)
            if result is None:
                no_coverage += 1
                print(f"  {zone.name}: coordinate outside/nodata in its own tile, left as-is")
                continue

            elevation, slope = result
            zone.elevation = round(elevation, 2)
            zone.slope = round(slope, 3) if slope is not None else 0.0
            zone.terrain_data_real = True
            enriched += 1
            print(f"  {zone.name}: real elevation={zone.elevation}m slope={zone.slope}deg")

        db.commit()
        print(f"\nEnriched {enriched}/{len(zones)} zone(s) with real terrain. {no_coverage} left honestly unavailable.")
        print("Run POST /weather/refresh-all next to compute real risk scores for the newly-enriched zones.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
