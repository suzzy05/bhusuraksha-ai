from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DataSourceSummary(BaseModel):
    """Safe for listing — no filesystem paths, no secrets."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str
    name: str
    category: str
    provider: Optional[str] = None
    configured: bool
    processed: bool
    last_status: str
    geographic_coverage: Optional[str] = None
    temporal_coverage: Optional[str] = None
    limitations: Optional[str] = None
    source_type: str


class DataSourceDetail(DataSourceSummary):
    """Fuller provenance detail — still no filesystem paths (only a
    filename) and no secrets/tokens."""

    official_source_url: Optional[str] = None
    license: Optional[str] = None
    citation: Optional[str] = None
    access_method: Optional[str] = None
    local_file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    downloaded_at: Optional[datetime] = None
    registered_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    processing_version: Optional[str] = None
    last_error: Optional[str] = None


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: str
    total_records: Optional[int] = None
    valid_records: Optional[int] = None
    invalid_records: Optional[int] = None
    inserted: Optional[int] = None
    duplicates: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    error_summary: Optional[str] = None


class DataSourceStatus(BaseModel):
    source_id: str
    last_status: str
    configured: bool
    processed: bool
    last_error: Optional[str] = None
    runs: List[IngestionRunOut]


class DataQualityReport(BaseModel):
    """Record-completeness metrics for one ingested source — a measure of
    how much of the schema the source dataset actually populated, NOT a
    measure of scientific/prediction accuracy. Labeled "Data Completeness"
    everywhere this is shown, never "quality" or "accuracy" in the UI."""

    source_id: str
    category: str
    latest_run: Optional[IngestionRunOut] = None
    stored_records: int
    with_coordinates: int
    # historical_landslide fields
    with_event_date: Optional[int] = None
    with_state: Optional[int] = None
    with_district: Optional[int] = None
    with_event_type: Optional[int] = None
    with_severity: Optional[int] = None
    # rainfall fields
    with_observed_date: Optional[int] = None
    with_station_id: Optional[int] = None
    with_rainfall_value: Optional[int] = None
