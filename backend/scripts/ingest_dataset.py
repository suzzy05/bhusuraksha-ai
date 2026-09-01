"""End-to-end manual dataset ingestion: verify file exists -> inspect ->
checksum -> register provenance -> validate -> process -> summarize.
Never modifies the original file; never downloads anything automatically.

Usage:
    python scripts/ingest_dataset.py \
        --category historical_landslide \
        --path data/raw/external/landslides.csv \
        --name "Example Landslide Inventory" \
        --source-url "https://official-source.example"

Row-level ingestion (into the database) is implemented for
`historical_landslide` and `rainfall`. `terrain`/`vegetation`/`boundary`
are single-file datasets (a DEM/land-cover raster or a boundary GeoJSON)
— these are registered and validated the same way, but "processing" means
extracting and storing real file metadata, not per-row ingestion.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.data_source import CATEGORIES  # noqa: E402
from ingestion.processors.boundaries import process_boundary_dataset  # noqa: E402
from ingestion.processors.landcover import process_landcover_dataset  # noqa: E402
from ingestion.processors.landslides import process_landslide_dataset  # noqa: E402
from ingestion.processors.rainfall import process_rainfall_dataset  # noqa: E402
from ingestion.processors.terrain import process_dem_dataset  # noqa: E402
from ingestion.provenance import complete_ingestion_run, register_manual_dataset, start_ingestion_run  # noqa: E402

PROCESSING_VERSION = "phase9-v1"
ROW_LEVEL_PROCESSORS = {
    "historical_landslide": process_landslide_dataset,
    "rainfall": process_rainfall_dataset,
}


def _process_metadata_only(category: str, path: Path, args) -> dict:
    if category == "terrain":
        return process_dem_dataset(path)
    if category == "vegetation":
        return process_landcover_dataset(path, year=args.year, classification=args.classification)
    if category == "boundary":
        return process_boundary_dataset(path)
    raise ValueError(f"No processor for category '{category}'")


def main():
    parser = argparse.ArgumentParser(description="Register and ingest a real external dataset")
    parser.add_argument("--category", required=True, choices=CATEGORIES)
    parser.add_argument("--path", required=True, help="Path to the dataset file")
    parser.add_argument("--name", required=True, help="Human-readable dataset name")
    parser.add_argument("--source-id", help="Stable identifier; derived from --name if omitted")
    parser.add_argument("--provider", help="Organization that produced the dataset")
    parser.add_argument("--source-url", help="Official source URL (only if actually known — never guessed)")
    parser.add_argument("--license", help="Dataset license / usage terms")
    parser.add_argument("--citation", help="How to cite this dataset")
    parser.add_argument("--geographic-coverage", help="Region(s) the dataset actually covers")
    parser.add_argument("--temporal-coverage", help="Date range the dataset actually covers")
    parser.add_argument("--limitations", help="Known gaps, resolution limits, biases")
    parser.add_argument("--year", help="Land cover dataset year (category=vegetation only)")
    parser.add_argument("--classification", help="Land cover classification scheme name (category=vegetation only)")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    source_id = args.source_id or args.name.strip().lower().replace(" ", "_")

    print("=" * 60)
    print("BHUSURAKSHA AI - DATASET INGESTION")
    print("=" * 60)
    print(f"source_id: {source_id}")
    print(f"category: {args.category}")
    print(f"path: {path.name}")

    db = SessionLocal()
    try:
        print("\nStep 1/3: Registering provenance (checksum + metadata)...")
        try:
            source = register_manual_dataset(
                db,
                source_id=source_id,
                name=args.name,
                category=args.category,
                path=path,
                provider=args.provider,
                official_source_url=args.source_url,
                license=args.license,
                citation=args.citation,
                geographic_coverage=args.geographic_coverage,
                temporal_coverage=args.temporal_coverage,
                limitations=args.limitations,
            )
        except Exception as exc:  # noqa: BLE001 - must fail clearly, not with a raw traceback
            print(f"Error: could not register dataset: {exc}")
            sys.exit(1)

        print(f"  checksum_sha256: {source.checksum_sha256}")
        print(f"  file_size_bytes: {source.file_size_bytes}")
        print(f"  configured: {source.configured}")

        print("\nStep 2/3: Processing...")
        run = start_ingestion_run(db, source_id)

        try:
            if args.category in ROW_LEVEL_PROCESSORS:
                summary = ROW_LEVEL_PROCESSORS[args.category](db, path, source_id, batch_size=args.batch_size)
                complete_ingestion_run(
                    db,
                    run,
                    total_records=summary.total_records,
                    valid_records=summary.valid_records,
                    invalid_records=summary.invalid_records,
                    inserted=summary.inserted,
                    duplicates=summary.duplicates,
                    success=True,
                    processing_version=PROCESSING_VERSION,
                )
            else:
                metadata = _process_metadata_only(args.category, path, args)
                available = bool(metadata.get("available"))
                complete_ingestion_run(
                    db,
                    run,
                    total_records=1,
                    valid_records=1 if available else 0,
                    invalid_records=0 if available else 1,
                    inserted=0,
                    duplicates=0,
                    success=available,
                    error_summary=None if available else metadata.get("reason"),
                    processing_version=PROCESSING_VERSION,
                )
                summary = metadata
                if not available:
                    print(f"\nProcessing could not complete: {metadata.get('reason')}")
                    print("Dataset remains registered but is marked 'failed' — nothing partial claims to be processed.")
                    sys.exit(1)
        except Exception as exc:  # noqa: BLE001 - must fail clearly, never leave a partial "processed" state
            complete_ingestion_run(
                db, run, total_records=0, valid_records=0, invalid_records=0, inserted=0, duplicates=0,
                success=False, error_summary=str(exc),
            )
            print(f"\nError during processing: {exc}")
            print("Dataset marked as failed — nothing partial was left claiming to be processed.")
            sys.exit(1)

        print("\nStep 3/3: Summary")
        print("=" * 60)
        if args.category in ROW_LEVEL_PROCESSORS:
            print(f"Total records:   {summary.total_records}")
            print(f"Valid records:   {summary.valid_records}")
            print(f"Invalid records: {summary.invalid_records}")
            print(f"Inserted:        {summary.inserted}")
            print(f"Duplicates:      {summary.duplicates}")
            if summary.rejected:
                preview = summary.rejected[:5]
                print(f"\nFirst {len(preview)} rejected record(s) (of {len(summary.rejected)}):")
                for rejected in preview:
                    print(f"  row {rejected.index}: {rejected.reasons}")
        else:
            print(f"Metadata: {summary}")
        print("\nStatus: processed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
