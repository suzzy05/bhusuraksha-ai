from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database import IS_POSTGRES, Base


class RainfallObservation(Base):
    """A real rainfall observation from a registered historical dataset —
    distinct from Phase 6's live-weather WeatherObservation (that's a
    single current reading per zone from Open-Meteo; this is historical,
    point-based, and dataset-sourced). `rainfall_mm` and `observed_date`
    are left NULL when the source record doesn't actually provide them.
    """

    __tablename__ = "rainfall_observations"

    id = Column(Integer, primary_key=True, index=True)

    source_id = Column(String, nullable=True, index=True)
    source_record_id = Column(String, nullable=True)
    # The observing station's real identifier from the source dataset —
    # distinct from source_record_id (a per-row id, never reused as a
    # dedup key here since one station recurs across many observations;
    # see ingestion/processors/rainfall.py).
    station_id = Column(String, nullable=True, index=True)

    observed_date = Column(DateTime, nullable=True, index=True)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)

    rainfall_mm = Column(Float, nullable=True)
    resolution = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


if IS_POSTGRES:
    from app.models.geo_utils import sync_point_geometry

    RainfallObservation.geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    sync_point_geometry(RainfallObservation)
