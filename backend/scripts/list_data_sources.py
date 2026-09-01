"""Lists registered dataset provenance from the database.

Usage:
    python scripts/list_data_sources.py
    python scripts/list_data_sources.py --category historical_landslide
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.data_source import CATEGORIES  # noqa: E402
from geospatial.source_registry import list_sources  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="List registered data sources")
    parser.add_argument("--category", choices=CATEGORIES)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        sources = list_sources(db, category=args.category)
    finally:
        db.close()

    print("=" * 60)
    print("BHUSURAKSHA AI - REGISTERED DATA SOURCES")
    print("=" * 60)

    if not sources:
        print("No data sources registered yet.")
        print("Register one with: python scripts/ingest_dataset.py --category ... --path ... --name ...")
        return

    for source in sources:
        print(f"\nsource_id: {source.source_id}")
        print(f"  name: {source.name}")
        print(f"  category: {source.category}")
        print(f"  source_type: {source.source_type}")
        print(f"  configured: {source.configured}")
        print(f"  processed: {source.processed}")
        print(f"  last_status: {source.last_status}")
        if source.last_error:
            print(f"  last_error: {source.last_error}")
        print(f"  geographic_coverage: {source.geographic_coverage or '(not documented)'}")
        print(f"  temporal_coverage: {source.temporal_coverage or '(not documented)'}")


if __name__ == "__main__":
    main()
