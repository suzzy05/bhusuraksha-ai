"""Historical rainfall dataset processor: CSV -> validated
RainfallObservation rows, batch-inserted. Distinct from Phase 6's live
weather (a single current Open-Meteo reading per zone) — this ingests a
real historical rainfall dataset (station records, gridded exports).
"""
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.rainfall_observation import RainfallObservation
from geospatial.loaders import load_dataset
from ingestion.schemas import IngestionSummary, RejectedRecord
from ingestion.storage import batched_insert
from ingestion.validation import parse_date_safely, validate_coordinates

EXTRA_ALIASES = {
    "rainfall": ["rainfall_mm", "RAINFALL", "rain_mm", "precip_mm", "PRCP"],
    # Deliberately NOT aliasing "station_id"/"id" into source_record_id: a
    # station or row id recurs across many observations from the same
    # station and is not a unique per-record identifier — using it for
    # dedup would wrongly collapse every reading from one station into
    # "duplicates". Only an explicit "record_id" column (one row = one id)
    # is trusted there; otherwise dedup falls back to the
    # (lat, lon, date) composite key below, which is the scientifically
    # correct notion of identity for point-in-time station observations.
    # station_id is captured separately, purely as descriptive metadata
    # (which real station produced this reading) — never used for dedup.
    "source_record_id": ["record_id"],
    "station_id": ["station_id", "STATION", "Station_ID", "station", "STATION_ID"],
}


def _row_get(row: dict, column_map: dict, field: str):
    column = column_map.get(field)
    if not column:
        return None
    value = row.get(column)
    if value is None or str(value).strip() == "":
        return None
    return value


def _existing_keys(db: Session, source_id: str):
    existing = (
        db.query(
            RainfallObservation.source_record_id,
            RainfallObservation.latitude,
            RainfallObservation.longitude,
            RainfallObservation.observed_date,
        )
        .filter(RainfallObservation.source_id == source_id)
        .all()
    )
    by_record_id = {row[0] for row in existing if row[0]}
    by_composite = {(round(row[1], 6), round(row[2], 6), row[3]) for row in existing}
    return by_record_id, by_composite


def process_rainfall_dataset(db: Session, path: Path, source_id: str, batch_size: int = 500) -> IngestionSummary:
    summary = IngestionSummary(source_id=source_id)

    dataset = load_dataset(path, column_aliases=EXTRA_ALIASES)
    rows = dataset["rows"]
    column_map = dataset["column_map"]
    summary.total_records = len(rows)

    existing_record_ids, existing_composite = _existing_keys(db, source_id)
    seen_record_ids = set()
    seen_composite = set()

    def _generate():
        for index, row in enumerate(rows):
            record_id = _row_get(row, column_map, "source_record_id")
            lat_raw = _row_get(row, column_map, "latitude")
            lon_raw = _row_get(row, column_map, "longitude")

            try:
                latitude = float(lat_raw) if lat_raw is not None else None
                longitude = float(lon_raw) if lon_raw is not None else None
            except (TypeError, ValueError):
                latitude = longitude = None

            coord_errors = validate_coordinates(latitude, longitude)
            if coord_errors:
                summary.invalid_records += 1
                summary.rejected.append(RejectedRecord(index=index, reasons=coord_errors, raw=dict(row)))
                continue

            rainfall_raw = _row_get(row, column_map, "rainfall")
            try:
                rainfall_mm = float(rainfall_raw) if rainfall_raw is not None else None
            except (TypeError, ValueError):
                rainfall_mm = None

            if rainfall_mm is not None and rainfall_mm < 0:
                summary.invalid_records += 1
                summary.rejected.append(RejectedRecord(index=index, reasons=["invalid_rainfall"], raw=dict(row)))
                continue

            observed_date = parse_date_safely(_row_get(row, column_map, "date"))
            station_id = _row_get(row, column_map, "station_id")
            composite_key = (round(latitude, 6), round(longitude, 6), observed_date)

            is_duplicate = False
            if record_id:
                if record_id in existing_record_ids or record_id in seen_record_ids:
                    is_duplicate = True
                seen_record_ids.add(record_id)
            else:
                if composite_key in existing_composite or composite_key in seen_composite:
                    is_duplicate = True
                seen_composite.add(composite_key)

            if is_duplicate:
                summary.duplicates += 1
                continue

            summary.valid_records += 1

            yield RainfallObservation(
                source_id=source_id,
                source_record_id=record_id,
                station_id=station_id,
                observed_date=observed_date,
                latitude=latitude,
                longitude=longitude,
                rainfall_mm=rainfall_mm,
            )

    summary.inserted = batched_insert(db, _generate(), batch_size=batch_size)
    return summary
