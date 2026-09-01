from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database import IS_POSTGRES, Base


class LandslideEvent(Base):
    """A historical landslide event record from a real, registered dataset.

    Any field the source dataset doesn't actually provide is left NULL —
    event_date/event_type/severity/state/district are never fabricated.
    `state`/`district` are populated either directly from the source
    dataset, or (Phase 9) from a real, configured boundary's point-in-polygon
    lookup — never guessed when no boundary is available (see
    geospatial/india/boundary.py).
    """

    __tablename__ = "landslide_events"

    id = Column(Integer, primary_key=True, index=True)

    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    state = Column(String, nullable=True, index=True)
    district = Column(String, nullable=True)

    event_date = Column(DateTime, nullable=True, index=True)
    event_type = Column(String, nullable=True)
    severity = Column(String, nullable=True)

    source_id = Column(String, nullable=True, index=True)
    source_record_id = Column(String, nullable=True)

    data_quality_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


if IS_POSTGRES:
    # PostGIS geometry column (SRID 4326 / WGS84), added only when actually
    # running against PostgreSQL+PostGIS — see monitoring_region.py for why
    # this is conditional rather than always present.
    from app.models.geo_utils import sync_point_geometry

    # spatial_index=False: Alembic's migration explicitly creates the GIST
    # index — see monitoring_region.py for why GeoAlchemy2's automatic
    # index-on-create-table behavior must be disabled here.
    LandslideEvent.geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    sync_point_geometry(LandslideEvent)
