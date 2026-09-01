"""Validation rules for records entering the geospatial pipeline.

Invalid records are never silently dropped: each rejected record is kept
in `invalid_records` together with the specific reason(s) it failed, so
nothing disappears without a trace.
"""
from typing import Dict, List, Tuple

LATITUDE_RANGE = (-90, 90)
LONGITUDE_RANGE = (-180, 180)
HUMIDITY_RANGE = (0, 100)
VEGETATION_RANGE = (0, 1)
SLOPE_RANGE = (0, 90)
# Generous real-world bound (Dead Sea shore to above Everest).
ELEVATION_RANGE = (-500, 9000)


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_coordinates(latitude, longitude) -> List[str]:
    lat, lon = _to_float(latitude), _to_float(longitude)
    if lat is None or lon is None:
        return ["missing_coordinates"]

    errors = []
    if not (LATITUDE_RANGE[0] <= lat <= LATITUDE_RANGE[1]):
        errors.append("invalid_latitude")
    if not (LONGITUDE_RANGE[0] <= lon <= LONGITUDE_RANGE[1]):
        errors.append("invalid_longitude")
    return errors


def validate_environmental_values(record: dict) -> List[str]:
    errors = []

    for field in ("rainfall_24h", "rainfall_7d"):
        value = _to_float(record.get(field))
        if value is not None and value < 0:
            errors.append(f"invalid_{field}")

    humidity = _to_float(record.get("humidity"))
    if humidity is not None and not (HUMIDITY_RANGE[0] <= humidity <= HUMIDITY_RANGE[1]):
        errors.append("invalid_humidity")

    vegetation = _to_float(record.get("vegetation"))
    if vegetation is not None and not (VEGETATION_RANGE[0] <= vegetation <= VEGETATION_RANGE[1]):
        errors.append("invalid_vegetation")

    slope = _to_float(record.get("slope"))
    if slope is not None and not (SLOPE_RANGE[0] <= slope <= SLOPE_RANGE[1]):
        errors.append("invalid_slope")

    elevation = _to_float(record.get("elevation"))
    if elevation is not None and not (ELEVATION_RANGE[0] <= elevation <= ELEVATION_RANGE[1]):
        errors.append("invalid_elevation")

    return errors


def validate_date(value) -> List[str]:
    if value is None or str(value).strip() == "":
        return ["missing_date"]
    return []


def _fingerprint(record: dict) -> Tuple:
    return (record.get("latitude"), record.get("longitude"), record.get("event_date"))


def validate_records(records: List[dict], require_date: bool = False) -> Dict:
    """Runs coordinate/environmental/(optional date) checks plus duplicate
    detection over `records`. Returns valid_records, invalid_records (each
    tagged with why it failed), and a validation_summary count block."""
    valid_records: List[dict] = []
    invalid_records: List[dict] = []
    seen = set()
    missing_coordinates = 0
    duplicates = 0

    for index, record in enumerate(records):
        errors = validate_coordinates(record.get("latitude"), record.get("longitude"))
        if "missing_coordinates" in errors:
            missing_coordinates += 1

        errors += validate_environmental_values(record)
        if require_date:
            errors += validate_date(record.get("event_date"))

        fingerprint = _fingerprint(record)
        has_real_fingerprint = fingerprint != (None, None, None)
        if has_real_fingerprint and fingerprint in seen:
            errors.append("duplicate_record")
            duplicates += 1
        elif has_real_fingerprint:
            seen.add(fingerprint)

        if errors:
            invalid_records.append({"index": index, "record": record, "errors": errors})
        else:
            valid_records.append(record)

    validation_summary = {
        "total_records": len(records),
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "missing_coordinates": missing_coordinates,
        "duplicates": duplicates,
    }

    return {
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "validation_summary": validation_summary,
    }
