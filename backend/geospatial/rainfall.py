"""Historical rainfall dataset architecture.

This is deliberately SEPARATE from Phase 6's live weather integration
(app/services/weather_service.py), which only fetches CURRENT conditions
from Open-Meteo for a single coordinate on demand. This module is for a
real historical rainfall dataset (station records, gridded reanalysis,
etc.) supporting 24h/7d/30d accumulation lookups — not yet integrated, and
never estimated from live weather as a substitute.
"""
from typing import Optional, Tuple

from geospatial.config import load_external_data_config


def _rainfall_dataset_status() -> Tuple[bool, str]:
    config = load_external_data_config()
    if config.rainfall_path is None:
        return False, "Historical rainfall dataset not configured."
    if not config.rainfall_path.exists():
        return False, "Configured rainfall dataset path does not exist."
    return False, "Rainfall dataset is configured, but historical accumulation lookup is not yet implemented."


def get_historical_rainfall(latitude: float, longitude: float, as_of: Optional[str] = None) -> dict:
    """Returns 24h/7d/30d historical rainfall accumulation for a
    coordinate from a real historical dataset. Not implemented in Phase 7
    — reports unavailable rather than substituting live weather data."""
    available, message = _rainfall_dataset_status()
    return {
        "rainfall_24h": None,
        "rainfall_7d": None,
        "rainfall_30d": None,
        "available": available,
        "message": message,
    }


def is_historical_rainfall_available() -> bool:
    return _rainfall_dataset_status()[0]
