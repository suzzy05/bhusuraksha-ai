"""Registers an external dataset's PROVENANCE metadata only — does not
download anything, does not modify the original file, and does not load
its rows into the database. For full ingestion (validate + process +
store rows), use scripts/ingest_dataset.py instead.

Usage:
    python scripts/register_data_source.py \
        --name "Landslide Dataset" \
        --category historical_landslide \
        --path data/raw/external/landslides.csv \
        --source-url "https://example.gov.in/dataset" \
        --license "..." \
        --geographic-coverage "..." \
        --temporal-coverage "..." \
        --limitations "..."
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from geospatial.loaders import DatasetLoadError, load_dataset  # noqa: E402
from ingestion.provenance import register_manual_dataset  # noqa: E402
from app.models.data_source import CATEGORIES  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Register provenance metadata for an already-downloaded external dataset"
    )
    parser.add_argument("--name", required=True, help="Human-readable dataset name")
    parser.add_argument("--category", required=True, choices=CATEGORIES)
    parser.add_argument("--path", required=True, help="Path to the dataset file (CSV or GeoJSON)")
    parser.add_argument("--source-id", help="Stable identifier; derived from --name if omitted")
    parser.add_argument("--source-url", help="Official source URL (only if actually known — never guessed)")
    parser.add_argument("--license", help="Dataset license / usage terms")
    parser.add_argument("--geographic-coverage", help="Region(s) the dataset actually covers")
    parser.add_argument("--temporal-coverage", help="Date range the dataset actually covers")
    parser.add_argument("--limitations", help="Known gaps, resolution limits, biases")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    try:
        dataset = load_dataset(path)
    except DatasetLoadError as exc:
        print(f"Error: could not inspect dataset: {exc}")
        sys.exit(1)

    source_id = args.source_id or args.name.strip().lower().replace(" ", "_")

    db = SessionLocal()
    try:
        entry = register_manual_dataset(
            db,
            source_id=source_id,
            name=args.name,
            category=args.category,
            path=path,
            official_source_url=args.source_url,
            license=args.license,
            geographic_coverage=args.geographic_coverage,
            temporal_coverage=args.temporal_coverage,
            limitations=args.limitations,
        )
    finally:
        db.close()

    print("=" * 60)
    print("BHUSURAKSHA AI - DATA SOURCE REGISTERED")
    print("=" * 60)
    print(f"source_id: {entry.source_id}")
    print(f"name: {entry.name}")
    print(f"category: {entry.category}")
    print(f"file_name: {entry.local_file_name}")
    print(f"row_count (this file, not persisted): {dataset['row_count']}")
    print(f"columns (this file, not persisted): {dataset['fieldnames']}")
    print(f"checksum_sha256: {entry.checksum_sha256}")
    print(f"configured: {entry.configured}")
    print()
    print("Note: this only records provenance metadata. It does not load")
    print("this dataset's rows into the database — use scripts/ingest_dataset.py for that.")


if __name__ == "__main__":
    main()
