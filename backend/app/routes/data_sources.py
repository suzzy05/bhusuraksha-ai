from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ingestion_run import IngestionRun
from app.models.landslide_event import LandslideEvent
from app.models.rainfall_observation import RainfallObservation
from app.schemas.data_source import DataQualityReport, DataSourceDetail, DataSourceStatus, DataSourceSummary
from geospatial.source_registry import get_source, list_sources

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


@router.get(
    "",
    response_model=List[DataSourceSummary],
    summary="List registered real/derived data sources",
    description="Read-only. Never exposes filesystem paths, secrets, or credential-bearing URLs — ingestion itself is CLI/admin-only (scripts/ingest_dataset.py).",
)
def list_data_sources(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    return list_sources(db, category=category)


@router.get("/{source_id}", response_model=DataSourceDetail)
def get_data_source(source_id: str, db: Session = Depends(get_db)):
    source = get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")
    return source


@router.get("/{source_id}/status", response_model=DataSourceStatus)
def get_data_source_status(source_id: str, db: Session = Depends(get_db)):
    source = get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

    runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.source_id == source_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(20)
        .all()
    )

    return DataSourceStatus(
        source_id=source.source_id,
        last_status=source.last_status,
        configured=source.configured,
        processed=source.processed,
        last_error=source.last_error,
        runs=runs,
    )


@router.get(
    "/{source_id}/quality",
    response_model=DataQualityReport,
    summary="Record-completeness metrics for one ingested source",
    description=(
        "Data Completeness only — how much of the schema this source's records actually populated. "
        "Not a measure of scientific or prediction accuracy. Only meaningful for row-level-ingested "
        "categories (historical_landslide, rainfall); other categories return zero stored_records."
    ),
)
def get_data_source_quality(source_id: str, db: Session = Depends(get_db)):
    source = get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

    latest_run = (
        db.query(IngestionRun)
        .filter(IngestionRun.source_id == source_id)
        .order_by(IngestionRun.started_at.desc())
        .first()
    )

    if source.category == "rainfall":
        observations = db.query(RainfallObservation).filter(RainfallObservation.source_id == source_id)
        stored = observations.count()
        return DataQualityReport(
            source_id=source_id,
            category=source.category,
            latest_run=latest_run,
            stored_records=stored,
            with_coordinates=observations.filter(
                RainfallObservation.latitude.isnot(None), RainfallObservation.longitude.isnot(None)
            ).count(),
            with_observed_date=observations.filter(RainfallObservation.observed_date.isnot(None)).count(),
            with_station_id=observations.filter(RainfallObservation.station_id.isnot(None)).count(),
            with_rainfall_value=observations.filter(RainfallObservation.rainfall_mm.isnot(None)).count(),
        )

    events = db.query(LandslideEvent).filter(LandslideEvent.source_id == source_id)
    stored = events.count()

    return DataQualityReport(
        source_id=source_id,
        category=source.category,
        latest_run=latest_run,
        stored_records=stored,
        with_coordinates=events.filter(
            LandslideEvent.latitude.isnot(None), LandslideEvent.longitude.isnot(None)
        ).count(),
        with_event_date=events.filter(LandslideEvent.event_date.isnot(None)).count(),
        with_state=events.filter(LandslideEvent.state.isnot(None)).count(),
        with_district=events.filter(LandslideEvent.district.isnot(None)).count(),
        with_event_type=events.filter(LandslideEvent.event_type.isnot(None)).count(),
        with_severity=events.filter(LandslideEvent.severity.isnot(None)).count(),
    )
