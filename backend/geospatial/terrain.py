"""Terrain data architecture — DEM elevation and slope derivation.

Phase 7 prepares the interface only. No DEM is downloaded automatically,
and no raster/GIS backend (e.g. rasterio/GDAL) is wired up yet, so these
functions never estimate a value — they report unavailable and say why.
"""
from typing import Tuple

from geospatial.config import load_external_data_config


def _dem_status() -> Tuple[bool, str]:
    config = load_external_data_config()
    if config.dem_path is None:
        return False, "Terrain (DEM) data not configured."
    if not config.dem_path.exists():
        return False, "Configured DEM path does not exist."
    return False, "DEM file is configured, but raster elevation/slope extraction is not yet implemented."


def get_elevation(latitude: float, longitude: float) -> dict:
    """Looks up elevation for a coordinate from a real DEM. Not
    implemented in Phase 7 — documented extension point, not a guess."""
    available, message = _dem_status()
    return {"elevation": None, "available": available, "message": message}


def calculate_slope_from_dem(latitude: float, longitude: float) -> dict:
    """Computes slope (degrees) from a real DEM's elevation gradient. Not
    implemented in Phase 7 for the same reason as get_elevation()."""
    available, message = _dem_status()
    return {"slope_degrees": None, "available": available, "message": message}


def is_terrain_data_available() -> bool:
    return _dem_status()[0]
