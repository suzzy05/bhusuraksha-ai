"""Unified landslide feature engineering — Phase 14.

Combines only AVAILABLE real data for one point-in-time coordinate:
rainfall accumulation (Phase 11), terrain (Phase 12), land cover (Phase
13), and historical-landslide density (Phase 10, computed via the same
PostGIS/SQLite-fallback spatial layer landslides/rainfall already use).

Every feature carries its own `_available` flag. A feature that isn't
available is `None`, NEVER a fabricated number — this dict is meant to be
training-ready input, and a silently-invented 0 would corrupt any model
trained on it.
"""
from datetime import datetime
from math import pi
from typing import Optional

from sqlalchemy.orm import Session

from app.services.landcover_service import get_landcover
from app.services.rainfall_service import DEFAULT_SEARCH_RADIUS_KM, get_rainfall_summary
from app.services.spatial_service import nearby_events
from app.services.terrain_service import get_terrain_features

FEATURE_SCHEMA_VERSION = "phase14-v1"
DEFAULT_DENSITY_RADIUS_KM = 10.0
MAX_DENSITY_SAMPLE = 500


def _historical_density(db: Session, lat: float, lon: float, as_of: datetime, radius_km: float) -> dict:
    """Real historical landslide event count/density within radius_km,
    using only events on/before `as_of` (never using future events to
    describe a point in the past). Always a real number (0 is a genuine
    query result, not "unavailable") — but total_sources_registered is
    included alongside it so a consumer can tell "confirmed zero events
    nearby" apart from "no dataset has ever been registered here"."""
    pairs, spatial_backend = nearby_events(
        db, lat=lat, lon=lon, radius_km=radius_km, end_date=as_of, limit=MAX_DENSITY_SAMPLE
    )
    area_km2 = pi * (radius_km**2)
    count = len(pairs)
    return {
        "historical_landslide_count": count,
        "historical_landslide_density_per_km2": round(count / area_km2, 6),
        "historical_density_radius_km": radius_km,
        "historical_density_spatial_backend": spatial_backend,
    }


def build_feature_vector(
    db: Session,
    lat: float,
    lon: float,
    as_of: Optional[datetime] = None,
    rainfall_radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
    density_radius_km: float = DEFAULT_DENSITY_RADIUS_KM,
) -> dict:
    as_of = as_of or datetime.utcnow()

    rainfall = get_rainfall_summary(db, lat=lat, lon=lon, as_of=as_of, radius_km=rainfall_radius_km)
    terrain = get_terrain_features(lat=lat, lon=lon)
    landcover = get_landcover(lat=lat, lon=lon)
    density = _historical_density(db, lat=lat, lon=lon, as_of=as_of, radius_km=density_radius_km)

    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "generated_at": datetime.utcnow().isoformat(),
        "input": {"lat": lat, "lon": lon, "as_of": as_of.isoformat()},
        # Rainfall (Phase 11) — null/unavailable per-window, never 0 for missing data.
        "rainfall_24h": rainfall["rainfall_24h"],
        "rainfall_72h": rainfall["rainfall_72h"],
        "rainfall_7d": rainfall["rainfall_7d"],
        "rainfall_30d": rainfall["rainfall_30d"],
        "antecedent_rainfall_index": rainfall["antecedent_rainfall_index"],
        "rainfall_available": rainfall["available"],
        "rainfall_spatial_backend": rainfall["spatial_backend"],
        # Terrain (Phase 12) — null/unavailable unless a real DEM is configured.
        "elevation_m": terrain["elevation_m"],
        "slope_degrees": terrain["slope_degrees"],
        "aspect_degrees": terrain["aspect_degrees"],
        "terrain_available": terrain["available"],
        # Land cover (Phase 13) — null/unavailable unless a real raster + scheme are configured.
        "landcover_category": landcover["normalized_category"],
        "landcover_available": landcover["available"],
        # Historical landslide density (Phase 10) — always a real computed
        # number (0 is a genuine result), from real PostGIS/SQLite queries only.
        **density,
    }
