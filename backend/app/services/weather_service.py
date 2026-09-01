"""Live weather data integration.

Provider-abstracted so the backing API can be swapped later without
touching callers (`app/routes/weather.py`, `risk_update_service.py`):
every provider exposes the same `get_current_weather(latitude, longitude)`
shape and returns a normalized dict where any field the provider didn't
actually supply is `None` — never fabricated.

Default provider: Open-Meteo (https://open-meteo.com) — free, no API key
required for this kind of prototype usage, supports arbitrary coordinates,
and provides real current + hourly precipitation data.

IMPORTANT — scientific limitation: current weather conditions alone do not
constitute a validated landslide early-warning model. Historical rainfall
accumulation, soil moisture/geology, terrain, vegetation, and validated
landslide inventories all matter too (see docs/WEATHER_LIMITATIONS.md).
This module only supplies one input signal among several.
"""
import os
from datetime import datetime, timezone
from typing import Optional

import requests

WEATHER_PROVIDER = os.getenv("WEATHER_PROVIDER", "open-meteo")

UNAVAILABLE_MESSAGE = "Live weather data is currently unavailable."
REQUEST_TIMEOUT_SECONDS = 6


def _empty_result(message: str = UNAVAILABLE_MESSAGE) -> dict:
    return {
        "temperature": None,
        "humidity": None,
        "rainfall_24h": None,
        "source": None,
        "observed_at": None,
        "available": False,
        "message": message,
    }


def _sum_last_24h_precipitation(hourly: dict, reference_time_str: Optional[str]) -> Optional[float]:
    times = hourly.get("time") or []
    values = hourly.get("precipitation") or []
    if not times or not values:
        return None

    try:
        reference = datetime.fromisoformat(reference_time_str) if reference_time_str else None
    except ValueError:
        reference = None

    total = 0.0
    counted = 0
    for time_str, value in zip(times, values):
        if value is None:
            continue
        try:
            sample_time = datetime.fromisoformat(time_str)
        except ValueError:
            continue
        if reference is not None:
            if sample_time > reference:
                continue
            if (reference - sample_time).total_seconds() > 24 * 3600:
                continue
        total += value
        counted += 1

    return round(total, 2) if counted else None


class WeatherProvider:
    name = "unknown"

    def get_current_weather(self, latitude: float, longitude: float) -> dict:
        raise NotImplementedError


class OpenMeteoProvider(WeatherProvider):
    name = "open-meteo"
    base_url = "https://api.open-meteo.com/v1/forecast"

    def get_current_weather(self, latitude: float, longitude: float) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m",
            "hourly": "precipitation",
            "past_days": 1,
            "forecast_days": 1,
            "timezone": "UTC",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            return _empty_result(f"{UNAVAILABLE_MESSAGE} ({exc.__class__.__name__})")

        current = payload.get("current") or {}
        hourly = payload.get("hourly") or {}
        observed_at = current.get("time")

        return {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "rainfall_24h": _sum_last_24h_precipitation(hourly, observed_at),
            "source": self.name,
            "observed_at": observed_at,
            "available": True,
        }


_PROVIDERS = {"open-meteo": OpenMeteoProvider()}

# Tracks whether a live weather fetch has actually succeeded during this
# process's lifetime — used by GET /data-status so "available" is never
# claimed before a real successful request has occurred.
_status = {"last_success_at": None, "last_attempt_available": False}


def is_provider_configured() -> bool:
    return WEATHER_PROVIDER in _PROVIDERS


def _get_provider() -> WeatherProvider:
    return _PROVIDERS.get(WEATHER_PROVIDER, _PROVIDERS["open-meteo"])


def get_current_weather(latitude: float, longitude: float) -> dict:
    if latitude is None or longitude is None:
        return _empty_result("Zone has no coordinates to fetch weather for.")

    try:
        result = _get_provider().get_current_weather(latitude, longitude)
    except Exception as exc:  # noqa: BLE001 - a provider must never crash the request
        result = _empty_result(f"{UNAVAILABLE_MESSAGE} ({exc.__class__.__name__})")

    _status["last_attempt_available"] = result["available"]
    if result["available"]:
        _status["last_success_at"] = datetime.now(timezone.utc).isoformat()

    return result


def get_live_weather_status() -> dict:
    return {
        "provider_configured": is_provider_configured(),
        "last_refresh": _status["last_success_at"],
        "available": _status["last_attempt_available"],
    }
