"""Real DEM point-feature extraction — Phase 12.

Returns elevation/slope/aspect for a single coordinate ONLY when a real
DEM is configured (BHUSURAKSHA_DEM_DATA_PATH) AND the optional `rasterio`
package is installed. Never estimates a value: every field is `None`
with `available: false` and a clear reason otherwise — this is the
honest, verifiable contract regardless of whether a real DEM exists.

Slope/aspect use Horn's method (Horn, 1981) — the same 3x3
finite-difference algorithm most desktop GIS "Slope"/"Aspect" tools use.
It requires a full 3x3 neighborhood, so a coordinate on the DEM's edge
gets an elevation but no slope/aspect (never fabricated at the boundary).
"""
from math import atan2, cos, degrees, hypot, radians
from typing import Optional, Tuple

METERS_PER_DEGREE_LAT = 111320.0

from geospatial.config import load_external_data_config


def _raster_backend_available() -> bool:
    try:
        import rasterio  # noqa: F401

        return True
    except ImportError:
        return False


def _status() -> Tuple[bool, Optional[str]]:
    config = load_external_data_config()
    if config.dem_path is None:
        return False, "Terrain (DEM) data not configured (BHUSURAKSHA_DEM_DATA_PATH is not set)."
    if not config.dem_path.exists():
        return False, "Configured DEM path does not exist."
    if not _raster_backend_available():
        return False, (
            "DEM is configured, but the optional 'rasterio' package is not installed "
            "(pip install -r requirements-optional.txt)."
        )
    return True, None


def is_terrain_data_available() -> bool:
    return _status()[0]


def _horn_slope_aspect(z, cellsize_x: float, cellsize_y: float):
    """`z` is a 3x3 neighborhood (row-major) centered on the target pixel.
    Returns (slope_degrees, aspect_degrees). Callers are responsible for
    only passing a full, in-bounds neighborhood (not at the raster edge)."""
    a, b, c = float(z[0, 0]), float(z[0, 1]), float(z[0, 2])
    d, _e, f = float(z[1, 0]), float(z[1, 1]), float(z[1, 2])
    g, h, i = float(z[2, 0]), float(z[2, 1]), float(z[2, 2])

    dz_dx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * cellsize_x)
    dz_dy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * cellsize_y)

    slope_degrees = degrees(atan2(hypot(dz_dx, dz_dy), 1.0))

    # Aspect (the compass direction a slope faces) is mathematically
    # undefined on flat ground — reported as None rather than an
    # arbitrary angle atan2(0, 0) would otherwise produce.
    if dz_dx == 0 and dz_dy == 0:
        return round(slope_degrees, 3), None

    aspect_degrees = 90.0 - degrees(atan2(dz_dy, -dz_dx))
    if aspect_degrees < 0:
        aspect_degrees += 360.0
    elif aspect_degrees > 360.0:
        aspect_degrees -= 360.0

    return round(slope_degrees, 3), round(aspect_degrees, 3)


def get_terrain_features(lat: float, lon: float) -> dict:
    available, message = _status()
    result = {
        "available": available,
        "elevation_m": None,
        "slope_degrees": None,
        "aspect_degrees": None,
        "message": message or "Computed from the configured DEM.",
    }
    if not available:
        return result

    import rasterio
    from rasterio.windows import Window

    config = load_external_data_config()
    try:
        with rasterio.open(config.dem_path) as dataset:
            row, col = dataset.index(lon, lat)
            if not (0 <= row < dataset.height and 0 <= col < dataset.width):
                return {**result, "available": False, "message": "Coordinate is outside the configured DEM's coverage."}

            # Read only the pixels actually needed (a 3x3 neighborhood, or a
            # single pixel at the raster's edge) — never the full band. For
            # a large real-world mosaic, reading the whole band on every
            # single point query would mean pulling gigabytes into memory
            # per call; a windowed read costs the same regardless of the
            # raster's overall size.
            has_neighborhood = 1 <= row <= dataset.height - 2 and 1 <= col <= dataset.width - 2
            if has_neighborhood:
                neighborhood = dataset.read(1, window=Window(col - 1, row - 1, 3, 3))
                elevation = float(neighborhood[1, 1])
            else:
                pixel = dataset.read(1, window=Window(col, row, 1, 1))
                elevation = float(pixel[0, 0])

            if dataset.nodata is not None and elevation == dataset.nodata:
                return {**result, "available": False, "message": "No DEM data at this coordinate (nodata value)."}

            cellsize_x, cellsize_y = dataset.res
            if dataset.crs and dataset.crs.is_geographic:
                # Horn's method needs ground distance, not angular degrees —
                # a DEM in EPSG:4326 (very common for SRTM/ASTER exports)
                # reports its resolution in degrees, which would silently
                # produce a nonsensical near-90-degree slope if used as-is.
                meters_per_degree_lon = METERS_PER_DEGREE_LAT * cos(radians(lat))
                cellsize_x = cellsize_x * meters_per_degree_lon
                cellsize_y = cellsize_y * METERS_PER_DEGREE_LAT

            if has_neighborhood:
                slope_degrees, aspect_degrees = _horn_slope_aspect(neighborhood, cellsize_x, cellsize_y)
            else:
                slope_degrees, aspect_degrees = None, None

            result["elevation_m"] = round(elevation, 2)
            result["slope_degrees"] = slope_degrees
            result["aspect_degrees"] = aspect_degrees
            if slope_degrees is None:
                result["message"] = "Elevation computed; slope/aspect need a full 3x3 neighborhood (coordinate is at the DEM's edge)."
            return result
    except Exception as exc:  # noqa: BLE001 - must report clearly, never crash the caller
        return {**result, "available": False, "message": f"Could not read the configured DEM: {exc}"}
