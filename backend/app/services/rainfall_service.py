"""Real historical rainfall accumulation — Phase 11.

Computes 24h/72h/7d/30d sums and an antecedent-rainfall index from actual
RainfallObservation rows near a point. A window is only ever populated
when at least one real observation actually falls inside it — a missing
window is `null`/`available: false`, NEVER 0 (0 means "confirmed no
rain", which is a claim we can't make from an absence of data).

Accumulation is computed from the single NEAREST station within the
search radius, never summed across multiple distinct stations (that would
mix unrelated physical locations' readings into a meaningless total).
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.services.spatial_service import nearby_rainfall

DEFAULT_SEARCH_RADIUS_KM = 25
MAX_LOOKBACK_DAYS = 30
ANTECEDENT_DAYS = 15
# A simple, widely-referenced "Antecedent Precipitation Index" form:
# API = sum(rainfall_i * decay^(days_ago_i)). A simplified soil-moisture
# PROXY from landslide literature, NOT a validated soil-moisture
# measurement or model input — labeled as such wherever it's shown.
ANTECEDENT_DECAY = 0.9

WINDOWS = {
    "rainfall_24h": 1,
    "rainfall_72h": 3,
    "rainfall_7d": 7,
    "rainfall_30d": 30,
}


def _station_key(obs) -> str:
    return obs.station_id or f"{round(obs.latitude, 4)},{round(obs.longitude, 4)}"


def _window_sum(observations, as_of: datetime, days: int):
    cutoff = as_of - timedelta(days=days)
    in_window = [obs for obs in observations if obs.observed_date and cutoff <= obs.observed_date <= as_of]
    if not in_window:
        return None, 0
    return round(sum(obs.rainfall_mm or 0 for obs in in_window), 2), len(in_window)


def _antecedent_index(observations, as_of: datetime):
    cutoff = as_of - timedelta(days=ANTECEDENT_DAYS)
    in_window = [obs for obs in observations if obs.observed_date and cutoff <= obs.observed_date <= as_of]
    if not in_window:
        return None, 0
    total = 0.0
    for obs in in_window:
        days_ago = max((as_of - obs.observed_date).total_seconds() / 86400.0, 0)
        total += (obs.rainfall_mm or 0) * (ANTECEDENT_DECAY**days_ago)
    return round(total, 2), len(in_window)


def get_rainfall_summary(
    db: Session,
    lat: float,
    lon: float,
    as_of: Optional[datetime] = None,
    radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
) -> dict:
    as_of = as_of or datetime.utcnow()

    pairs, backend = nearby_rainfall(
        db,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        start_date=as_of - timedelta(days=MAX_LOOKBACK_DAYS),
        end_date=as_of,
        limit=2000,
    )

    base = {
        "spatial_backend": backend,
        "search_radius_km": radius_km,
        "as_of": as_of.isoformat(),
        "nearest_station_id": None,
        "nearest_station_distance_km": None,
        **{key: None for key in WINDOWS},
        **{f"{key}_observation_count": 0 for key in WINDOWS},
        "antecedent_rainfall_index": None,
        "antecedent_observation_count": 0,
        "available": False,
        "message": "No rainfall station found within the search radius.",
    }

    if not pairs:
        return base

    # Use only the single nearest station's own readings — never mixed
    # across distinct physical stations.
    nearest_obs, nearest_distance = pairs[0]
    nearest_key = _station_key(nearest_obs)
    station_observations = [obs for obs, _distance in pairs if _station_key(obs) == nearest_key]

    result = dict(base)
    result["nearest_station_id"] = nearest_obs.station_id
    result["nearest_station_distance_km"] = round(nearest_distance, 3)
    result["available"] = True
    result["message"] = "Computed from real historical observations at the nearest station within range."

    for key, days in WINDOWS.items():
        total, count = _window_sum(station_observations, as_of, days)
        result[key] = total
        result[f"{key}_observation_count"] = count

    antecedent, antecedent_count = _antecedent_index(station_observations, as_of)
    result["antecedent_rainfall_index"] = antecedent
    result["antecedent_observation_count"] = antecedent_count

    return result
