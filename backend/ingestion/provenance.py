"""Higher-level provenance orchestration for the ingestion CLI: computes
checksums, registers a DataSource with full Phase 9 metadata (building on
geospatial.source_registry's DB-backed CRUD), and records one
IngestionRun per processing attempt as an auditable history.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun
from geospatial.source_registry import register_source, update_status
from ingestion.checksum import file_size_bytes, sha256_of_file


def register_manual_dataset(
    db: Session,
    source_id: str,
    name: str,
    category: str,
    path: Path,
    provider: Optional[str] = None,
    official_source_url: Optional[str] = None,
    license: Optional[str] = None,  # noqa: A002
    citation: Optional[str] = None,
    geographic_coverage: Optional[str] = None,
    temporal_coverage: Optional[str] = None,
    limitations: Optional[str] = None,
    source_type: str = "external_real",
):
    checksum = sha256_of_file(path)
    size = file_size_bytes(path)

    return register_source(
        db,
        source_id=source_id,
        name=name,
        category=category,
        file_path=str(path),
        provider=provider,
        official_source_url=official_source_url,
        license=license,
        citation=citation,
        geographic_coverage=geographic_coverage,
        temporal_coverage=temporal_coverage,
        limitations=limitations,
        access_method="manual",
        checksum_sha256=checksum,
        file_size_bytes=size,
        source_type=source_type,
    )


def start_ingestion_run(db: Session, source_id: str) -> IngestionRun:
    update_status(db, source_id, status="validated")
    run = IngestionRun(source_id=source_id, status="processing", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)
    update_status(db, source_id, status="processing")
    return run


def complete_ingestion_run(
    db: Session,
    run: IngestionRun,
    total_records: int,
    valid_records: int,
    invalid_records: int,
    inserted: int,
    duplicates: int,
    success: bool,
    error_summary: Optional[str] = None,
    processing_version: Optional[str] = None,
) -> IngestionRun:
    run.total_records = total_records
    run.valid_records = valid_records
    run.invalid_records = invalid_records
    run.inserted = inserted
    run.duplicates = duplicates
    run.completed_at = datetime.utcnow()
    run.status = "processed" if success else "failed"
    run.error_summary = error_summary
    db.commit()
    db.refresh(run)

    # A dataset is only ever marked `processed=true` when ingestion
    # genuinely completed successfully — never on a failed/partial run.
    update_status(
        db,
        run.source_id,
        status="processed" if success else "failed",
        error=error_summary,
        processed=success,
        processing_version=processing_version,
    )
    return run
