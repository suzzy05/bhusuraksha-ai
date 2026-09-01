"""Geospatial feature engineering.

Every function here is honest about what it can and cannot compute from
the data actually supplied — none of them fabricate a value. Where the
required input is missing, the output stays `None` rather than being
estimated or guessed.
"""
from datetime import datetime, timedelta
from typing import List, Optional


def calculate_slope(elevation_grid=None, dem_path=None) -> Optional[float]:
    """Computes terrain slope (degrees) from a DEM.

    Phase 3 does not ship a raster/GIS backend (e.g. rasterio/GDAL), so
    this is a documented extension point: once a real DEM is supplied and
    a raster backend is added, this function should compute slope from
    the elevation gradient. Until then it never pretends a DEM-derived
    slope exists — it returns None when no DEM input is given, and raises
    clearly if a DEM *is* given but cannot actually be processed yet.
    """
    if elevation_grid is None and dem_path is None:
        return None
    raise NotImplementedError(
        "DEM-based slope calculation requires a raster backend not yet integrated "
        "(see docs/DATA_SOURCES.md). Provide a `slope` column directly in the "
        "source dataset instead."
    )


def normalize_vegetation(value, source_scale: str = "0-1") -> Optional[float]:
    """Normalizes a vegetation/land-cover reading onto 0.0-1.0.

    `source_scale` documents the assumed input range:
      - "0-1":   already normalized (e.g. rescaled NDVI) — passed through.
      - "0-100": a percentage cover value.
      - "ndvi":  raw NDVI (-1 to 1), rescaled onto 0-1.
    """
    if value is None or value == "":
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if source_scale == "0-100":
        normalized = value / 100.0
    elif source_scale == "ndvi":
        normalized = (value + 1.0) / 2.0
    else:
        normalized = value

    return round(max(0.0, min(1.0, normalized)), 4)


def calculate_rainfall_windows(timeseries: Optional[List[dict]], as_of: Optional[datetime] = None) -> dict:
    """Given `[{"date": ..., "rainfall": ...}, ...]` readings for ONE
    location, sums rainfall over the 24h/7d windows ending at `as_of` (or
    the latest reading if not given).

    Returns `{"rainfall_24h": None, "rainfall_7d": None}` when there isn't
    enough time-series data to compute a real window — this never
    fabricates a rainfall figure.
    """
    if not timeseries:
        return {"rainfall_24h": None, "rainfall_7d": None}

    parsed = []
    for entry in timeseries:
        try:
            date = datetime.fromisoformat(str(entry["date"]))
            rainfall = float(entry["rainfall"])
        except (KeyError, ValueError, TypeError):
            continue
        parsed.append((date, rainfall))

    if not parsed:
        return {"rainfall_24h": None, "rainfall_7d": None}

    parsed.sort(key=lambda item: item[0])
    reference = as_of or parsed[-1][0]

    window_24h = [r for d, r in parsed if reference - timedelta(hours=24) <= d <= reference]
    window_7d = [r for d, r in parsed if reference - timedelta(days=7) <= d <= reference]

    return {
        "rainfall_24h": round(sum(window_24h), 2) if window_24h else None,
        "rainfall_7d": round(sum(window_7d), 2) if window_7d else None,
    }


def historical_landslide_flag(record: dict) -> Optional[bool]:
    """True when this record IS a historical-landslide inventory entry.

    Extension point: flagging OTHER (non-inventory) records as
    `historical_landslide=True` based on geographic proximity to a known
    inventory point requires a spatial join (e.g. haversine radius search
    against the loaded inventory) — not implemented in Phase 3. This only
    reads an explicit flag/kind already present on the record.
    """
    if record.get("dataset_kind") == "landslide_inventory":
        return True
    value = record.get("historical_landslide")
    if value is None or value == "":
        return None
    return str(value).strip().lower() in ("true", "1", "yes")


# Weights for calculate_data_quality — a category earns its weight only
# when at least one of its fields is present, since a source dataset
# rarely supplies every field in a category.
_DATA_QUALITY_WEIGHTS = {
    "coordinates": 25,
    "environmental": 25,
    "terrain": 20,
    "historical": 20,
    "date": 10,
}
_COORDINATE_FIELDS = ["latitude", "longitude"]
_ENVIRONMENTAL_FIELDS = ["rainfall_24h", "rainfall_7d", "humidity", "temperature"]
_TERRAIN_FIELDS = ["slope", "elevation", "vegetation"]


def calculate_data_quality(record: dict) -> dict:
    """Scores data COMPLETENESS from 0-100 — this is NOT a landslide risk
    score, and must never be confused with one.

    +25 coordinates present, +25 any environmental reading present,
    +20 any terrain reading present, +20 historical_landslide known,
    +10 event_date present. `missing_features` lists every individual
    field (not just categories) that came back empty, for transparency.
    """
    score = 0
    missing: List[str] = []

    if all(record.get(f) is not None for f in _COORDINATE_FIELDS):
        score += _DATA_QUALITY_WEIGHTS["coordinates"]
    missing += [f for f in _COORDINATE_FIELDS if record.get(f) is None]

    if any(record.get(f) is not None for f in _ENVIRONMENTAL_FIELDS):
        score += _DATA_QUALITY_WEIGHTS["environmental"]
    missing += [f for f in _ENVIRONMENTAL_FIELDS if record.get(f) is None]

    if any(record.get(f) is not None for f in _TERRAIN_FIELDS):
        score += _DATA_QUALITY_WEIGHTS["terrain"]
    missing += [f for f in _TERRAIN_FIELDS if record.get(f) is None]

    if record.get("historical_landslide") is not None:
        score += _DATA_QUALITY_WEIGHTS["historical"]
    else:
        missing.append("historical_landslide")

    if record.get("event_date"):
        score += _DATA_QUALITY_WEIGHTS["date"]
    else:
        missing.append("event_date")

    return {"data_quality_score": score, "missing_features": missing}
