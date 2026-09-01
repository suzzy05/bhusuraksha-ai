"""India administrative boundary support.

No boundary is downloaded automatically. If a boundary env var is unset
(or the configured file doesn't exist), the application continues to
work fine — anything that would use it (e.g. a spatial state/district
lookup for a coordinate) reports unavailable rather than fabricating a
boundary or guessing a name. When a real GeoJSON boundary IS configured,
point-in-polygon lookups are genuinely computed (pure-Python ray casting
— no GDAL/shapely dependency needed for this).
"""
import json
import os
from pathlib import Path
from typing import Optional

ENV_INDIA_BOUNDARY_PATH = "BHUSURAKSHA_INDIA_BOUNDARY_PATH"
ENV_STATE_BOUNDARY_PATH = "BHUSURAKSHA_STATE_BOUNDARY_PATH"
ENV_DISTRICT_BOUNDARY_PATH = "BHUSURAKSHA_DISTRICT_BOUNDARY_PATH"
NOT_CONFIGURED_MESSAGE = "India boundary dataset not configured."

# Common property-name candidates for a feature's human-readable name,
# tried in order — real boundary files vary in convention.
NAME_FIELDS = ("name", "NAME", "STATE", "State", "state", "DISTRICT", "District", "district", "NAME_1", "NAME_2")

_geojson_cache: dict = {}


def _get_path(env_var: str) -> Optional[Path]:
    raw = os.getenv(env_var)
    return Path(raw) if raw else None


def get_boundary_path() -> Optional[Path]:
    """Backward-compatible accessor for the national boundary path."""
    return _get_path(ENV_INDIA_BOUNDARY_PATH)


def _load_geojson(path: Path) -> Optional[dict]:
    key = str(path)
    if key in _geojson_cache:
        return _geojson_cache[key]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    _geojson_cache[key] = data
    return data


def _point_in_ring(x: float, y: float, ring) -> bool:
    """Standard ray-casting point-in-polygon test for one linear ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(x: float, y: float, geometry: dict) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return False
    if gtype == "Polygon":
        if not _point_in_ring(x, y, coords[0]):
            return False
        return not any(_point_in_ring(x, y, hole) for hole in coords[1:])
    if gtype == "MultiPolygon":
        return any(_point_in_geometry(x, y, {"type": "Polygon", "coordinates": polygon}) for polygon in coords)
    return False


def find_region_for_point(latitude: float, longitude: float, boundary_path: Optional[Path]) -> Optional[str]:
    """Returns the name of the boundary feature containing this point, or
    None if no boundary is configured/available, or none contains it.
    Never guesses a name."""
    if boundary_path is None or not boundary_path.exists():
        return None
    data = _load_geojson(boundary_path)
    if not data:
        return None

    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        if _point_in_geometry(longitude, latitude, geometry):
            props = feature.get("properties") or {}
            for field in NAME_FIELDS:
                if props.get(field):
                    return props[field]
            return None
    return None


def get_state_for_point(latitude: float, longitude: float) -> Optional[str]:
    return find_region_for_point(latitude, longitude, _get_path(ENV_STATE_BOUNDARY_PATH))


def get_district_for_point(latitude: float, longitude: float) -> Optional[str]:
    return find_region_for_point(latitude, longitude, _get_path(ENV_DISTRICT_BOUNDARY_PATH))


def _status_for(path: Optional[Path]) -> dict:
    if path is None:
        return {"configured": False, "available": False}
    if not path.exists():
        return {"configured": True, "available": False}
    if _load_geojson(path) is None:
        return {"configured": True, "available": False}
    return {"configured": True, "available": True}


def get_boundary_status() -> dict:
    india_path = _get_path(ENV_INDIA_BOUNDARY_PATH)
    state_path = _get_path(ENV_STATE_BOUNDARY_PATH)
    district_path = _get_path(ENV_DISTRICT_BOUNDARY_PATH)

    any_configured = any([india_path, state_path, district_path])
    return {
        "india": _status_for(india_path),
        "state": _status_for(state_path),
        "district": _status_for(district_path),
        "message": None if any_configured else NOT_CONFIGURED_MESSAGE,
    }
