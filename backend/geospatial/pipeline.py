"""Orchestrates the Phase 3 geospatial data pipeline:

    external dataset -> loader -> column mapping -> validation ->
    normalization (GeoRiskRecord) -> feature engineering ->
    data quality assessment -> processed dataset

Only the historical landslide inventory becomes the primary processed
record set. A supplementary rainfall dataset is loaded and validated but
NOT spatially/temporally joined onto the landslide records — matching
rainfall stations/grids to landslide locations by distance and date is a
documented extension point (see docs/DATA_SOURCES.md), not implemented
here, so this pipeline never fabricates a location-specific rainfall
figure for a landslide record from an unjoined dataset.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from geospatial.config import NOT_CONFIGURED_MESSAGE, load_external_data_config
from geospatial.feature_engineering import calculate_data_quality, historical_landslide_flag, normalize_vegetation
from geospatial.loaders import DatasetLoadError, load_landslide_inventory, load_rainfall_dataset
from geospatial.schemas import ML_FEATURE_FIELDS, SourceType
from geospatial.validators import validate_records

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_RECORDS_FILENAME = "processed_landslide_records.csv"
PROCESSED_METADATA_FILENAME = "processed_landslide_metadata.json"

RECORD_FIELDNAMES = [
    "location_id",
    "latitude",
    "longitude",
    "event_date",
    "rainfall_24h",
    "rainfall_7d",
    "humidity",
    "temperature",
    "elevation",
    "slope",
    "vegetation",
    "historical_landslide",
    "risk_level",
    "source_type",
    "source_name",
    "data_quality_score",
    "missing_features",
]

PIPELINE_LIMITATIONS = [
    "Rainfall/DEM/vegetation datasets are validated independently and are NOT spatially "
    "or temporally joined onto landslide records in Phase 3 — see docs/DATA_SOURCES.md.",
    "risk_level is left unset for every external record; Phase 3 does not fabricate labels "
    "for real-world data.",
    "Slope/elevation are only populated when the source dataset already provides them — "
    "no DEM/raster processing is performed.",
]


def _row_get(row: dict, column_map: dict, field: str):
    column = column_map.get(field)
    if not column:
        return None
    value = row.get(column)
    if value is None or str(value).strip() == "":
        return None
    return value


def _to_float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_landslide_row(row: dict, column_map: dict, source_name: str, index: int) -> dict:
    """Maps one raw landslide-inventory row onto the common GeoRiskRecord
    fields via flexible column mapping. Any field the source dataset
    doesn't have stays explicitly None — nothing is guessed or invented."""
    record = {
        "location_id": _row_get(row, column_map, "location_id") or f"{source_name}-{index}",
        "latitude": _to_float_or_none(_row_get(row, column_map, "latitude")),
        "longitude": _to_float_or_none(_row_get(row, column_map, "longitude")),
        "event_date": _row_get(row, column_map, "date"),
        "rainfall_24h": _to_float_or_none(_row_get(row, column_map, "rainfall_24h")),
        "rainfall_7d": _to_float_or_none(_row_get(row, column_map, "rainfall_7d")),
        "humidity": _to_float_or_none(_row_get(row, column_map, "humidity")),
        "temperature": _to_float_or_none(_row_get(row, column_map, "temperature")),
        "elevation": _to_float_or_none(_row_get(row, column_map, "elevation")),
        "slope": _to_float_or_none(_row_get(row, column_map, "slope")),
        "dataset_kind": "landslide_inventory",
        "risk_level": None,
        "source_type": SourceType.EXTERNAL.value,
        "source_name": source_name,
    }
    record["vegetation"] = normalize_vegetation(_row_get(row, column_map, "vegetation"))
    record["historical_landslide"] = historical_landslide_flag(record)
    return record


def _finalize_record(record: dict) -> dict:
    quality = calculate_data_quality(record)
    record["data_quality_score"] = quality["data_quality_score"]
    record["missing_features"] = quality["missing_features"]
    return record


def _write_processed_csv(records, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RECORD_FIELDNAMES)
        writer.writeheader()
        for record in records:
            row = {name: record.get(name) for name in RECORD_FIELDNAMES}
            row["missing_features"] = ";".join(record.get("missing_features", []))
            writer.writerow(row)


def run_pipeline(
    landslide_path: Optional[str] = None,
    rainfall_path: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Runs the pipeline with whatever datasets are actually provided —
    it works fine with only one, and never raises for a missing/bad path;
    errors are reported per-dataset in the returned dict instead."""
    output_dir = Path(output_dir) if output_dir else PROCESSED_DIR
    result = {
        "landslide": None,
        "rainfall": None,
        "processed_output": None,
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        "limitations": PIPELINE_LIMITATIONS,
    }

    if landslide_path is None and rainfall_path is None:
        result["error"] = "No dataset path provided."
        return result

    processed_records = []

    if landslide_path is not None:
        try:
            dataset = load_landslide_inventory(landslide_path)
        except DatasetLoadError as exc:
            result["landslide"] = {"error": str(exc)}
        else:
            normalized = [
                normalize_landslide_row(row, dataset["column_map"], dataset["source_name"], i)
                for i, row in enumerate(dataset["rows"])
            ]
            validation = validate_records(normalized)
            processed_records = [_finalize_record(r) for r in validation["valid_records"]]

            result["landslide"] = {
                "source_name": dataset["source_name"],
                "file_type": dataset["file_type"],
                "records": dataset["row_count"],
                **validation["validation_summary"],
            }

    if rainfall_path is not None:
        try:
            dataset = load_rainfall_dataset(rainfall_path)
        except DatasetLoadError as exc:
            result["rainfall"] = {"error": str(exc)}
        else:
            result["rainfall"] = {
                "source_name": dataset["source_name"],
                "file_type": dataset["file_type"],
                "records": dataset["row_count"],
            }

    if processed_records:
        records_path = output_dir / PROCESSED_RECORDS_FILENAME
        _write_processed_csv(processed_records, records_path)

        observed_missing = sorted({f for r in processed_records for f in r.get("missing_features", [])})
        landslide_summary = result.get("landslide") or {}
        metadata = {
            # Filenames only — never an absolute filesystem path.
            "source_landslide_file": Path(landslide_path).name if landslide_path else None,
            "source_rainfall_file": Path(rainfall_path).name if rainfall_path else None,
            "processing_timestamp": result["processing_timestamp"],
            "total_input_records": landslide_summary.get("records", 0),
            "valid_records": len(processed_records),
            "invalid_records": landslide_summary.get("invalid_records", 0),
            "missing_features_observed": observed_missing,
            "ml_feature_alignment": ML_FEATURE_FIELDS,
            "limitations": PIPELINE_LIMITATIONS,
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / PROCESSED_METADATA_FILENAME, "w") as f:
            json.dump(metadata, f, indent=2)

        result["processed_output"] = {
            "records_file": PROCESSED_RECORDS_FILENAME,
            "metadata_file": PROCESSED_METADATA_FILENAME,
            "record_count": len(processed_records),
        }

    return result


def run_pipeline_from_config(output_dir: Optional[Path] = None) -> dict:
    """Runs the pipeline using whatever BHUSURAKSHA_*_DATA_PATH env vars
    are set. Returns a clear "not configured" result instead of crashing
    if none are set."""
    config = load_external_data_config()
    if config.landslide_path is None and config.rainfall_path is None:
        return {"error": NOT_CONFIGURED_MESSAGE, **config.status()}

    return run_pipeline(
        landslide_path=str(config.landslide_path) if config.landslide_path else None,
        rainfall_path=str(config.rainfall_path) if config.rainfall_path else None,
        output_dir=output_dir,
    )
