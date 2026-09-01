"""Computes the `real_data` block of GET /data-status. Every value is
queried live — never hardcoded, never assumed from documentation.
"""
from sqlalchemy.orm import Session

from app.models.data_source import DataSource
from app.models.landslide_event import LandslideEvent
from app.models.rainfall_observation import RainfallObservation
from geospatial.india.boundary import get_boundary_status
from ingestion.base import CONFIGURED
from ingestion.connectors.dem import DemConnector
from ingestion.connectors.landcover import LandcoverConnector


def get_real_data_status(db: Session) -> dict:
    sources_registered = db.query(DataSource).count()
    sources_processed = db.query(DataSource).filter(DataSource.processed.is_(True)).count()
    landslide_events = db.query(LandslideEvent).count()
    rainfall_observations = db.query(RainfallObservation).count()

    dem_available = DemConnector().status().state == CONFIGURED
    landcover_available = LandcoverConnector().status().state == CONFIGURED
    boundary_status = get_boundary_status()
    boundaries_available = any(boundary_status[level]["available"] for level in ("india", "state", "district"))

    return {
        "sources_registered": sources_registered,
        "sources_processed": sources_processed,
        "landslide_events": landslide_events,
        "rainfall_observations": rainfall_observations,
        "dem_available": dem_available,
        "landcover_available": landcover_available,
        "boundaries_available": boundaries_available,
    }
