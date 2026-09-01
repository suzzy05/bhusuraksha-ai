"""Inspects a CSV or GeoJSON dataset WITHOUT modifying it.

Usage:
    python scripts/inspect_dataset.py path/to/dataset.csv
    python scripts/inspect_dataset.py path/to/dataset.geojson
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geospatial.loaders import DatasetLoadError, detect_file_type, load_csv, load_geojson  # noqa: E402


def _bounding_box(rows, lat_col, lon_col):
    lats, lons = [], []
    for row in rows:
        try:
            lats.append(float(row[lat_col]))
            lons.append(float(row[lon_col]))
        except (KeyError, TypeError, ValueError):
            continue
    if not lats or not lons:
        return None
    return {
        "min_latitude": min(lats),
        "max_latitude": max(lats),
        "min_longitude": min(lons),
        "max_longitude": max(lons),
    }


def _missing_value_counts(rows, fieldnames):
    counts = {name: 0 for name in fieldnames}
    for row in rows:
        for name in fieldnames:
            value = row.get(name)
            if value is None or str(value).strip() == "":
                counts[name] += 1
    return counts


def inspect(path_str: str):
    path = Path(path_str)
    print("=" * 60)
    print("BHUSURAKSHA AI - DATASET INSPECTION")
    print("=" * 60)
    print(f"File: {path}")

    if not path.exists():
        print("Error: file not found.")
        return

    try:
        file_type = detect_file_type(path)
        dataset = load_csv(path) if file_type == "csv" else load_geojson(path)
    except DatasetLoadError as exc:
        print(f"Error: {exc}")
        return

    rows = dataset["rows"]
    fieldnames = dataset["fieldnames"]
    column_map = dataset["column_map"]

    print(f"File type: {dataset['file_type']}")
    if dataset["file_type"] == "geojson":
        print(f"Geometry type: {dataset.get('geometry_type') or 'unknown'}")
    print(f"Row count: {dataset['row_count']}")
    print(f"Columns ({len(fieldnames)}): {fieldnames}")

    print("\nDetected columns:")
    print(f"  Latitude column: {column_map.get('latitude') or 'not detected'}")
    print(f"  Longitude column: {column_map.get('longitude') or 'not detected'}")
    print(f"  Date column: {column_map.get('date') or 'not detected'}")

    if not rows:
        print("\nDataset has no rows.")
        print()
        return

    print("\nMissing values per column:")
    missing_counts = _missing_value_counts(rows, fieldnames)
    if any(missing_counts.values()):
        for name, count in missing_counts.items():
            if count:
                print(f"  {name}: {count} missing ({count / len(rows):.1%})")
    else:
        print("  none")

    print("\nSample rows (up to 3):")
    for row in rows[:3]:
        print(f"  {row}")

    lat_col, lon_col = column_map.get("latitude"), column_map.get("longitude")
    print("\nGeographic bounding box:")
    if lat_col and lon_col:
        bbox = _bounding_box(rows, lat_col, lon_col)
        print(f"  {bbox}" if bbox else "  Could not compute (no valid coordinate values)")
    else:
        print("  unavailable (latitude/longitude columns not detected)")

    print()


def main():
    parser = argparse.ArgumentParser(description="Inspect a CSV or GeoJSON dataset without modifying it")
    parser.add_argument("path", help="Path to the dataset file")
    args = parser.parse_args()
    inspect(args.path)


if __name__ == "__main__":
    main()
