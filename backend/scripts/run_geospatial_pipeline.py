"""CLI wrapper around geospatial.pipeline.run_pipeline.

Works with just one dataset or both:

    python scripts/run_geospatial_pipeline.py --landslide path/to/landslides.csv
    python scripts/run_geospatial_pipeline.py --landslide path/to/landslides.csv --rainfall path/to/rainfall.csv
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geospatial.pipeline import run_pipeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="BHUSURAKSHA AI geospatial data pipeline")
    parser.add_argument("--landslide", help="Path to a historical landslide inventory CSV/GeoJSON")
    parser.add_argument("--rainfall", help="Path to a rainfall dataset CSV/GeoJSON")
    args = parser.parse_args()

    if not args.landslide and not args.rainfall:
        parser.error("Provide at least one of --landslide or --rainfall")

    result = run_pipeline(landslide_path=args.landslide, rainfall_path=args.rainfall)

    print("=" * 60)
    print("BHUSURAKSHA AI GEOSPATIAL PIPELINE")
    print("=" * 60)

    if result.get("error"):
        print(result["error"])
        return

    landslide = result.get("landslide")
    if landslide is not None:
        print("\nHistorical Landslide Data:")
        if "error" in landslide:
            print(f"  Error: {landslide['error']}")
        else:
            print(f"  Records: {landslide['records']}")
            print(f"  Valid: {landslide['valid_records']}")
            print(f"  Invalid: {landslide['invalid_records']}")
            print(f"  Missing coordinates: {landslide['missing_coordinates']}")
            print(f"  Duplicates: {landslide['duplicates']}")

    rainfall = result.get("rainfall")
    if rainfall is not None:
        print("\nRainfall Data:")
        if "error" in rainfall:
            print(f"  Error: {rainfall['error']}")
        else:
            print(f"  Records: {rainfall['records']}")

    print("\nProcessed Output:")
    if result.get("processed_output"):
        output = result["processed_output"]
        print(f"  data/processed/{output['records_file']}")
        print(f"  data/processed/{output['metadata_file']}")
        print(f"  Records written: {output['record_count']}")
    else:
        print("  none (no valid landslide records to write)")

    print("\nLimitations:")
    for note in result.get("limitations", []):
        print(f"  - {note}")
    print()


if __name__ == "__main__":
    main()
