"""Generic spatial point queries — PostGIS-backed on PostgreSQL, with an
explicitly-labeled, non-indexed fallback on SQLite so local dev keeps
working. Never pretends SQLite has PostGIS: every SQLite response carries
`spatial_backend: "sqlite_approximate"` (radius) or `"sqlite_exact"`
(bbox) so callers can always tell which path served the request.

Shared by LandslideEvent (Phase 10) and RainfallObservation (Phase 11) —
both are simple point models (latitude/longitude/geom/source_id), only
differing in which column holds their date. Parameterized by model class
+ date column rather than duplicated per model.
"""
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import List, Optional, Tuple

from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.database import IS_POSTGRES
from app.models.landslide_event import LandslideEvent
from app.models.rainfall_observation import RainfallObservation

if IS_POSTGRES:
    from geoalchemy2 import Geography

EARTH_RADIUS_KM = 6371.0088
# Hard safety cap so a huge inventory can never be pulled into Python whole
# for the SQLite haversine fallback — the bounding-box pre-filter below
# keeps this from being hit in practice for a reasonable radius.
SQLITE_CANDIDATE_CAP = 5000


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))


def _apply_common_filters(query, model, date_column, source_id, start_date, end_date):
    if source_id:
        query = query.filter(model.source_id == source_id)
    if start_date:
        query = query.filter(date_column >= start_date)
    if end_date:
        query = query.filter(date_column <= end_date)
    return query


def _nearby_points(
    db: Session,
    model,
    date_column,
    lat: float,
    lon: float,
    radius_km: float,
    source_id: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    limit: int,
) -> Tuple[List[Tuple[object, float]], str]:
    """Returns (list of (row, distance_km) sorted nearest-first, backend_label)."""
    if IS_POSTGRES:
        point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        point_geog = cast(point, Geography)
        geom_geog = cast(model.geom, Geography)
        distance_km = func.ST_Distance(geom_geog, point_geog) / 1000.0

        query = db.query(model, distance_km.label("distance_km")).filter(
            func.ST_DWithin(geom_geog, point_geog, radius_km * 1000.0)
        )
        query = _apply_common_filters(query, model, date_column, source_id, start_date, end_date)
        rows = query.order_by(distance_km).limit(limit).all()
        return [(row, float(distance)) for row, distance in rows], "postgis"

    # SQLite fallback: a degrees-per-km bounding-box pre-filter (cheap, uses
    # the existing lat/lon indexes) narrows candidates before an exact
    # Python haversine distance + radius filter — never a full table scan
    # of an unbounded inventory, but also never claiming index-accelerated
    # spatial search the way PostGIS provides.
    deg_lat = radius_km / 111.32
    cos_lat = max(cos(radians(lat)), 0.01)
    deg_lon = radius_km / (111.32 * cos_lat)

    query = db.query(model).filter(
        model.latitude.between(lat - deg_lat, lat + deg_lat),
        model.longitude.between(lon - deg_lon, lon + deg_lon),
    )
    query = _apply_common_filters(query, model, date_column, source_id, start_date, end_date)
    candidates = query.limit(SQLITE_CANDIDATE_CAP).all()

    scored = [(row, _haversine_km(lat, lon, row.latitude, row.longitude)) for row in candidates]
    within_radius = [pair for pair in scored if pair[1] <= radius_km]
    within_radius.sort(key=lambda pair: pair[1])
    return within_radius[:limit], "sqlite_approximate"


def _bbox_points(
    db: Session,
    model,
    date_column,
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    source_id: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    limit: int,
) -> Tuple[List[object], int, str]:
    """Returns (rows, total_matching, backend_label). `total_matching` lets
    the caller report `truncated` without pulling the full set into memory."""
    if IS_POSTGRES:
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        query = db.query(model).filter(func.ST_Intersects(model.geom, envelope))
        backend = "postgis"
    else:
        # A lat/lon bounding box is exact regardless of backend (unlike a
        # radius search, no geodesic math is involved), so this is not an
        # approximation — just not index-accelerated the way PostGIS is.
        query = db.query(model).filter(
            model.latitude.between(min_lat, max_lat),
            model.longitude.between(min_lon, max_lon),
        )
        backend = "sqlite_exact"

    query = _apply_common_filters(query, model, date_column, source_id, start_date, end_date)
    total_matching = query.count()
    results = query.order_by(date_column.desc().nullslast()).limit(limit).all()
    return results, total_matching, backend


def nearby_events(db: Session, lat, lon, radius_km, source_id=None, start_date=None, end_date=None, limit=100):
    return _nearby_points(
        db, LandslideEvent, LandslideEvent.event_date, lat, lon, radius_km, source_id, start_date, end_date, limit
    )


def bbox_events(db: Session, min_lat, min_lon, max_lat, max_lon, source_id=None, start_date=None, end_date=None, limit=500):
    return _bbox_points(
        db, LandslideEvent, LandslideEvent.event_date,
        min_lat, min_lon, max_lat, max_lon, source_id, start_date, end_date, limit,
    )


def nearby_rainfall(db: Session, lat, lon, radius_km, source_id=None, start_date=None, end_date=None, limit=100):
    return _nearby_points(
        db, RainfallObservation, RainfallObservation.observed_date,
        lat, lon, radius_km, source_id, start_date, end_date, limit,
    )


def bbox_rainfall(db: Session, min_lat, min_lon, max_lat, max_lon, source_id=None, start_date=None, end_date=None, limit=500):
    return _bbox_points(
        db, RainfallObservation, RainfallObservation.observed_date,
        min_lat, min_lon, max_lat, max_lon, source_id, start_date, end_date, limit,
    )
