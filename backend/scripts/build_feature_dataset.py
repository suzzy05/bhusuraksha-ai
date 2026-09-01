"""Phase 14 — builds a real feature-engineered dataset from registered
LandslideEvent rows: raw data -> spatial association -> feature
extraction -> quality checks -> CSV + metadata JSON.

Every row's features come from app.services.feature_engineering_service
(rainfall/terrain/land-cover/historical-density) — nothing here estimates
a missing value. If zero LandslideEvent rows are registered, this
produces an empty (header-only) dataset and says so plainly, rather than
fabricating rows.

Usage:
    python scripts/build_feature_dataset.py
    python scripts/build_feature_dataset.py --output data/processed/my_dataset.csv
"""
import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.landslide_event import LandslideEvent  # noqa: E402
from app.services.feature_engineering_service import (  # noqa: E402
    FEATURE_SCHEMA_VERSION,
    build_feature_vector,
)

DEFAULT_OUTPUT = "data/processed/landslide_features.csv"
FEATURE_COLUMNS = [
    "source_event_id",
    "latitude",
    "longitude",
    "as_of",
    "rainfall_24h",
    "rainfall_72h",
    "rainfall_7d",
    "rainfall_30d",
    "antecedent_rainfall_index",
    "rainfall_available",
    "elevation_m",
    "slope_degrees",
    "aspect_degrees",
    "terrain_available",
    "landcover_category",
    "landcover_available",
    "historical_landslide_count",
    "historical_landslide_density_per_km2",
]


def main():
    parser = argparse.ArgumentParser(description="Build a feature-engineered dataset from registered LandslideEvent rows")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = output_path.with_suffix(".metadata.json")

    db = SessionLocal()
    try:
        events = db.query(LandslideEvent).order_by(LandslideEvent.id).all()

        print("=" * 60)
        print("BHUSURAKSHA AI - FEATURE DATASET BUILD (Phase 14)")
        print("=" * 60)
        print(f"Source: {len(events)} registered LandslideEvent row(s)")

        if not events:
            print("\nNo real historical landslide events are registered — writing an")
            print("empty (header-only) dataset. Nothing is fabricated to fill it.")

        rows = []
        availability = {"rainfall": 0, "terrain": 0, "landcover": 0}
        for event in events:
            as_of = event.event_date or event.created_at
            features = build_feature_vector(db, lat=event.latitude, lon=event.longitude, as_of=as_of)
            row = {
                "source_event_id": event.id,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "as_of": features["input"]["as_of"],
                **{col: features[col] for col in FEATURE_COLUMNS if col in features},
            }
            rows.append(row)
            if features["rainfall_available"]:
                availability["rainfall"] += 1
            if features["terrain_available"]:
                availability["terrain"] += 1
            if features["landcover_available"]:
                availability["landcover"] += 1

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        metadata = {
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "generated_at": datetime.utcnow().isoformat(),
            "source_record_count": len(events),
            "output_row_count": len(rows),
            "feature_availability": {
                "rainfall": availability["rainfall"],
                "terrain": availability["terrain"],
                "landcover": availability["landcover"],
            },
            "note": (
                "This is a feature-engineered dataset for future ML work, NOT itself a trained model or "
                "a validated ML training run. See docs/ML_LIMITATIONS.md."
            ),
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"\nWrote {len(rows)} row(s) to {output_path}")
        print(f"Wrote metadata to {metadata_path}")
        print(f"Feature availability: rainfall={availability['rainfall']}/{len(rows)}, "
              f"terrain={availability['terrain']}/{len(rows)}, landcover={availability['landcover']}/{len(rows)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
