"""Registry of external dataset provenance — backed by the `DataSource`
table (app/models/data_source.py) now that PostgreSQL is available.

Evolved from Phase 7's JSON-file registry: same purpose (every external
dataset must be registered with real provenance before it counts as
integrated; `configured` is only true once the file was actually found
and inspected, never from documentation alone), now queryable via the
Phase 9 `/data-sources` API and joined against `IngestionRun` history.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.data_source import CATEGORIES, DataSource  # noqa: F401 - re-exported for callers

__all__ = ["CATEGORIES", "list_sources", "get_source", "register_source", "update_status"]


def list_sources(db: Session, category: Optional[str] = None) -> List[DataSource]:
    query = db.query(DataSource)
    if category:
        query = query.filter(DataSource.category == category)
    return query.order_by(DataSource.source_id).all()


def get_source(db: Session, source_id: str) -> Optional[DataSource]:
    return db.query(DataSource).filter(DataSource.source_id == source_id).first()


def register_source(
    db: Session,
    source_id: str,
    name: str,
    category: str,
    file_path: Optional[str],
    provider: Optional[str] = None,
    official_source_url: Optional[str] = None,
    license: Optional[str] = None,  # noqa: A002 - matches the spec's field name
    citation: Optional[str] = None,
    geographic_coverage: Optional[str] = None,
    temporal_coverage: Optional[str] = None,
    limitations: Optional[str] = None,
    access_method: Optional[str] = "manual",
    checksum_sha256: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    downloaded_at: Optional[datetime] = None,
    source_type: str = "external_real",
) -> DataSource:
    """Records provenance metadata for a dataset. Never downloads or
    modifies the dataset itself — `file_path` must already exist locally
    for `configured` to be set true."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category '{category}'. Expected one of {CATEGORIES}.")

    configured = bool(file_path) and Path(file_path).exists()

    source = get_source(db, source_id)
    if source is None:
        source = DataSource(source_id=source_id)
        db.add(source)

    source.name = name
    source.category = category
    source.provider = provider
    source.official_source_url = official_source_url
    source.license = license
    source.citation = citation
    source.geographic_coverage = geographic_coverage
    source.temporal_coverage = temporal_coverage
    source.access_method = access_method
    source.local_file_name = Path(file_path).name if file_path else None
    source.file_size_bytes = file_size_bytes
    source.checksum_sha256 = checksum_sha256
    source.downloaded_at = downloaded_at
    source.configured = configured
    source.limitations = limitations
    source.source_type = source_type
    source.last_status = "registered"
    source.last_error = None
    source.registered_at = source.registered_at or datetime.utcnow()

    db.commit()
    db.refresh(source)
    return source


def update_status(
    db: Session,
    source_id: str,
    status: str,
    error: Optional[str] = None,
    processed: Optional[bool] = None,
    processing_version: Optional[str] = None,
) -> Optional[DataSource]:
    source = get_source(db, source_id)
    if source is None:
        return None

    source.last_status = status
    source.last_error = error
    if processed is not None:
        source.processed = processed
        if processed:
            source.processed_at = datetime.utcnow()
    if processing_version is not None:
        source.processing_version = processing_version

    db.commit()
    db.refresh(source)
    return source
