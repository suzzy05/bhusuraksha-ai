"""Real land-cover point classification — Phase 13.

Returns a normalized category (forest/grassland/cropland/urban/bare_land/
water/unknown) for a single coordinate ONLY when a real land-cover raster
is configured (BHUSURAKSHA_LANDCOVER_PATH) AND rasterio is installed.
Never fabricates a category: unconfigured/unreadable/out-of-coverage all
report available: false with a clear reason.

The raw class code is only ever mapped to a normalized category via an
explicitly configured, real, published legend (BHUSURAKSHA_LANDCOVER_SCHEME
— see geospatial/landcover_schemes.py); an unset or unrecognized scheme
returns the raw code with normalized_category="unknown" rather than
guessing what the numbers mean.
"""
import os
from typing import Optional, Tuple

from geospatial.landcover_schemes import normalize_class
from ingestion.connectors.dem import raster_backend_available
from ingestion.connectors.landcover import ENV_PATH

ENV_SCHEME = "BHUSURAKSHA_LANDCOVER_SCHEME"


def _status() -> Tuple[bool, Optional[str], Optional[str]]:
    raw = os.getenv(ENV_PATH)
    if not raw:
        return False, None, f"Land cover data not configured ({ENV_PATH} is not set)."
    from pathlib import Path

    path = Path(raw)
    if not path.exists():
        return False, None, "Configured land cover path does not exist."
    if not raster_backend_available():
        return False, None, (
            "Land cover is configured, but the optional 'rasterio' package is not installed "
            "(pip install -r requirements-optional.txt)."
        )
    return True, raw, None


def is_landcover_available() -> bool:
    return _status()[0]


def get_landcover(lat: float, lon: float) -> dict:
    available, path, message = _status()
    result = {
        "available": available,
        "raw_class": None,
        "normalized_category": None,
        "scheme": os.getenv(ENV_SCHEME),
        "message": message or "Computed from the configured land cover raster.",
    }
    if not available:
        return result

    import rasterio
    from rasterio.windows import Window

    try:
        with rasterio.open(path) as dataset:
            row, col = dataset.index(lon, lat)
            if not (0 <= row < dataset.height and 0 <= col < dataset.width):
                return {**result, "available": False, "message": "Coordinate is outside the configured raster's coverage."}

            # A single-pixel windowed read — never the full band, which for
            # a large real-world mosaic would mean pulling the whole raster
            # into memory on every single point query.
            pixel = dataset.read(1, window=Window(col, row, 1, 1))
            raw_class = pixel[0, 0]
            if dataset.nodata is not None and raw_class == dataset.nodata:
                return {**result, "available": False, "message": "No land cover data at this coordinate (nodata value)."}

            scheme = os.getenv(ENV_SCHEME)
            result["raw_class"] = int(raw_class)
            result["normalized_category"] = normalize_class(scheme, raw_class)
            if not scheme:
                result["message"] = (
                    "Raw class code read from the raster, but BHUSURAKSHA_LANDCOVER_SCHEME is not set — "
                    "normalized_category is 'unknown' rather than guessed."
                )
            return result
    except Exception as exc:  # noqa: BLE001 - must report clearly, never crash the caller
        return {**result, "available": False, "message": f"Could not read the configured land cover raster: {exc}"}
