"""Modular dataset loaders for the geospatial pipeline.

Loaders never assume a fixed schema — column names vary a lot between
real-world sources, so every loader detects columns via a flexible alias
table (customizable per call) instead of hardcoding exact header names.
Loaders validate that the file exists and is a supported type, and raise
`DatasetLoadError` with a clear message otherwise; they never crash with a
raw traceback.
"""
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# Alias lists used to detect a logical field from a dataset's actual header
# names. Callers can override or extend this per-loader via `column_aliases`.
DEFAULT_COLUMN_ALIASES: Dict[str, List[str]] = {
    "location_id": ["location_id", "id", "ID", "site_id", "station_id"],
    "latitude": ["latitude", "lat", "Latitude", "LAT", "Lat", "y"],
    "longitude": ["longitude", "lon", "lng", "Longitude", "LON", "Lng", "x"],
    "date": ["date", "event_date", "Date", "DATE", "timestamp", "event_time"],
    "event_type": ["event_type", "type", "EventType", "landslide_type"],
    "severity": ["severity", "magnitude", "Severity"],
    "rainfall_24h": ["rainfall_24h", "rainfall24h", "rain_24h"],
    "rainfall_7d": ["rainfall_7d", "rainfall7d", "rain_7d"],
    "rainfall": ["rainfall", "precipitation", "rain_mm", "Rainfall"],
    "humidity": ["humidity", "relative_humidity", "Humidity"],
    "temperature": ["temperature", "temp", "Temperature"],
    "elevation": ["elevation", "altitude", "Elevation", "dem"],
    "slope": ["slope", "slope_degrees", "Slope"],
    "vegetation": ["vegetation", "ndvi", "NDVI", "vegetation_index", "land_cover"],
    "historical_landslide": ["historical_landslide", "landslide", "is_landslide"],
}


class DatasetLoadError(Exception):
    """Raised for any dataset problem (missing file, bad format, ...).
    Always carries a clear, user-facing message."""


def _detect_column(fieldnames: Sequence[str], aliases: Sequence[str]) -> Optional[str]:
    lower_map = {name.lower(): name for name in fieldnames}
    for alias in aliases:
        match = lower_map.get(alias.lower())
        if match:
            return match
    return None


def _merge_aliases(
    base: Dict[str, List[str]], extra: Optional[Dict[str, List[str]]]
) -> Dict[str, List[str]]:
    """Merges alias lists per field name (extending, not replacing) — a
    caller adding e.g. a "record_id" alias for "source_record_id" should
    never lose the built-in "id"/"ID" aliases for an existing field like
    "date" just because it also wanted to add "eventDate"."""
    merged = {field: list(values) for field, values in base.items()}
    for field, values in (extra or {}).items():
        existing = merged.setdefault(field, [])
        for alias in values:
            if alias not in existing:
                existing.append(alias)
    return merged


def _build_column_map(fieldnames: Sequence[str], column_aliases: Optional[Dict[str, List[str]]]) -> Dict[str, Optional[str]]:
    aliases = _merge_aliases(DEFAULT_COLUMN_ALIASES, column_aliases)
    return {field: _detect_column(fieldnames, alias_list) for field, alias_list in aliases.items()}


def detect_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in (".geojson", ".json"):
        return "geojson"
    raise DatasetLoadError(f"Unsupported file type '{suffix or '(none)'}' — expected .csv or .geojson")


def load_csv(path, column_aliases: Optional[Dict[str, List[str]]] = None) -> dict:
    path = Path(path)
    if not path.exists():
        raise DatasetLoadError(f"File not found: {path.name}")

    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except (csv.Error, UnicodeDecodeError) as exc:
        raise DatasetLoadError(f"Could not parse CSV '{path.name}': {exc}") from exc

    return {
        "rows": rows,
        "fieldnames": fieldnames,
        "column_map": _build_column_map(fieldnames, column_aliases),
        "row_count": len(rows),
        "source_path": path.name,
        "file_type": "csv",
    }


def load_geojson(path, column_aliases: Optional[Dict[str, List[str]]] = None) -> dict:
    path = Path(path)
    if not path.exists():
        raise DatasetLoadError(f"File not found: {path.name}")

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetLoadError(f"Could not parse GeoJSON '{path.name}': {exc}") from exc

    features = data.get("features", []) if isinstance(data, dict) else []
    if not isinstance(features, list):
        raise DatasetLoadError(f"'{path.name}' does not look like a GeoJSON FeatureCollection")

    rows: List[dict] = []
    geometry_type = None
    for feature in features:
        properties = dict((feature or {}).get("properties") or {})
        geometry = (feature or {}).get("geometry") or {}
        geometry_type = geometry_type or geometry.get("type")
        if geometry.get("type") == "Point":
            coords = geometry.get("coordinates") or [None, None]
            properties.setdefault("longitude", coords[0] if len(coords) > 0 else None)
            properties.setdefault("latitude", coords[1] if len(coords) > 1 else None)
        rows.append(properties)

    fieldnames = sorted({key for row in rows for key in row.keys()})

    return {
        "rows": rows,
        "fieldnames": fieldnames,
        "column_map": _build_column_map(fieldnames, column_aliases),
        "row_count": len(rows),
        "source_path": path.name,
        "file_type": "geojson",
        "geometry_type": geometry_type,
    }


def load_dataset(path, column_aliases: Optional[Dict[str, List[str]]] = None) -> dict:
    path = Path(path)
    file_type = detect_file_type(path)
    if file_type == "csv":
        return load_csv(path, column_aliases)
    return load_geojson(path, column_aliases)


def load_landslide_inventory(path, source_name: str = "external_landslide_inventory", column_aliases=None) -> dict:
    dataset = load_dataset(path, column_aliases)
    dataset["source_name"] = source_name
    dataset["dataset_kind"] = "landslide_inventory"
    return dataset


def load_rainfall_dataset(path, source_name: str = "external_rainfall_data", column_aliases=None) -> dict:
    dataset = load_dataset(path, column_aliases)
    dataset["source_name"] = source_name
    dataset["dataset_kind"] = "rainfall"
    return dataset
