from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base

# historical_landslide, rainfall, terrain, vegetation, boundary
CATEGORIES = ("historical_landslide", "rainfall", "terrain", "vegetation", "boundary")

SOURCE_TYPES = ("demo_synthetic", "external_real", "derived")

INGESTION_STATES = ("registered", "validated", "processing", "processed", "failed")


class DataSource(Base):
    """Provenance record for one external (or derived) dataset.

    Evolved from Phase 7's JSON-file registry (geospatial/source_registry.py)
    into a proper table now that PostgreSQL is available — needed for the
    Phase 9 /data-sources API, status filtering, and an auditable ingestion
    history (see IngestionRun). `local_file_name` is a filename only, never
    an absolute path — this row is safe to return from an API.
    """

    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=False, unique=True, index=True)

    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=True)
    official_source_url = Column(String, nullable=True)
    license = Column(String, nullable=True)
    citation = Column(String, nullable=True)
    geographic_coverage = Column(String, nullable=True)
    temporal_coverage = Column(String, nullable=True)

    # "manual" | "configured_download"
    access_method = Column(String, nullable=True)

    local_file_name = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    checksum_sha256 = Column(String, nullable=True)

    downloaded_at = Column(DateTime, nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    processing_version = Column(String, nullable=True)

    # configured=true only once the local file was actually found and
    # inspected; processed=true only once ingestion genuinely completed.
    configured = Column(Boolean, nullable=False, default=False)
    processed = Column(Boolean, nullable=False, default=False)

    last_status = Column(String, nullable=False, default="registered")
    last_error = Column(String, nullable=True)

    limitations = Column(String, nullable=True)
    source_type = Column(String, nullable=False, default="external_real")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
