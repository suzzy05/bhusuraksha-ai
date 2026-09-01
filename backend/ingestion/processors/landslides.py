"""Historical landslide dataset processor: CSV/GeoJSON -> validated,
deduplicated LandslideEvent rows, batch-inserted with a full processing
summary. Reuses geospatial.loaders for file parsing/column-alias
detection (Phase 3) rather than duplicating it.
"""
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.landslide_event import LandslideEvent
from geospatial.india.boundary import get_district_for_point, get_state_for_point
from geospatial.loaders import load_dataset
from ingestion.schemas import IngestionSummary, RejectedRecord
from ingestion.storage import batched_insert
from ingestion.validation import parse_date_safely, validate_coordinates

# Extra column aliases beyond geospatial.loaders' defaults, specific to
# real-world landslide inventory exports.
EXTRA_ALIASES = {
    "date": ["eventDate", "EVENT_DATE", "Event_Date"],
    "event_type": ["EVENT_TYPE", "landslide_category"],
    "severity": ["SEVERITY", "fatality_class", "hazard_type", "landslide_size"],
    "source_record_id": ["record_id", "id", "ID", "OBJECTID", "fid", "event_id"],
    "state": ["state", "State", "STATE", "admin_division_name"],
    "district": ["district", "District", "DISTRICT"],
}


def _row_get(row: dict, column_map: dict, field: str):
    column = column_map.get(field)
    if not column:
        return None
    value = row.get(column)
    if value is None or str(value).strip() == "":
        return None
    return value


def _quality_score(event_date, event_type, severity, state) -> int:
    """0-100 record completeness — NOT a risk indicator. Coordinates are
    always present at this point (already validated)."""
    score = 40
    score += 20 if event_date else 0
    score += 15 if event_type else 0
    score += 15 if severity else 0
    score += 10 if state else 0
    return score


def _existing_keys(db: Session, source_id: str):
    """Loads identity keys already stored for this source, so re-running
    ingestion never blindly duplicates rows. Prefers source_record_id;
    falls back to a (lat, lon, date) composite — coordinates alone are
    never treated as a unique key, since different events can share a
    location."""
    existing = (
        db.query(
            LandslideEvent.source_record_id,
            LandslideEvent.latitude,
            LandslideEvent.longitude,
            LandslideEvent.event_date,
        )
        .filter(LandslideEvent.source_id == source_id)
        .all()
    )
    by_record_id = {row[0] for row in existing if row[0]}
    by_composite = {(round(row[1], 6), round(row[2], 6), row[3]) for row in existing}
    return by_record_id, by_composite


def process_landslide_dataset(
    db: Session, path: Path, source_id: str, batch_size: int = 500
) -> IngestionSummary:
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
            record_id = _row_get(row, column_map, "source_record_id") or _row_get(row, column_map, "location_id")
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

            event_date = parse_date_safely(_row_get(row, column_map, "date"))
            composite_key = (round(latitude, 6), round(longitude, 6), event_date)

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

            state = _row_get(row, column_map, "state")
            district = None
            if state is None:
                # Only ever filled from a REAL configured boundary — never guessed.
                state = get_state_for_point(latitude, longitude)
                district = get_district_for_point(latitude, longitude)

            event_type = _row_get(row, column_map, "event_type")
            severity = _row_get(row, column_map, "severity")

            yield LandslideEvent(
                latitude=latitude,
                longitude=longitude,
                state=state,
                district=district,
                event_date=event_date,
                event_type=event_type,
                severity=severity,
                source_id=source_id,
                source_record_id=record_id,
                data_quality_score=_quality_score(event_date, event_type, severity, state or district),
            )

    summary.inserted = batched_insert(db, _generate(), batch_size=batch_size)
    return summary
