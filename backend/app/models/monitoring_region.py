from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String

from app.database import IS_POSTGRES, Base

REGION_TYPES = ("state", "district", "point", "grid_cell", "custom_region")


class MonitoringRegion(Base):
    """A scalable geographic entity for pan-India monitoring coverage.

    Deliberately NOT bulk-populated with a synthetic India-wide grid —
    rows are only created when backed by an actual registered dataset (or,
    for now, left empty). `coverage_score` reflects DATA COMPLETENESS for
    this region, never landslide risk.
    """

    __tablename__ = "monitoring_regions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    state = Column(String, nullable=True, index=True)
    district = Column(String, nullable=True)

    region_type = Column(String, nullable=False, default="point")

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Only populated when a real geometry (e.g. a state/district polygon)
    # is actually supplied — never fabricated. Kept alongside `geom` below
    # (rather than replaced by it) so existing API responses stay compatible.
    geometry_type = Column(String, nullable=True)
    geometry_data = Column(JSON, nullable=True)

    # Null means "unknown" — never guessed.
    is_landslide_prone = Column(Boolean, nullable=True)

    source_id = Column(String, nullable=True, index=True)
    source_type = Column(String, nullable=False, default="demo_seed")

    # 0-100 DATA coverage/completeness score — NOT a risk score.
    coverage_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


if IS_POSTGRES:
    # PostGIS geometry column (SRID 4326 / WGS84), added only when actually
    # running against PostgreSQL+PostGIS. GeoAlchemy2's Geometry type
    # requires SpatiaLite on SQLite, which local development deliberately
    # does not install — so on SQLite this column simply does not exist.
    from app.models.geo_utils import sync_point_geometry

    # spatial_index=False: Alembic's migration explicitly creates the GIST
    # index (see alembic/versions/) — leaving GeoAlchemy2's own automatic
    # index-on-create-table behavior enabled would create a second,
    # conflicting index of the same name.
    MonitoringRegion.geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    sync_point_geometry(MonitoringRegion)
