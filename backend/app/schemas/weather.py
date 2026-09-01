from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class WeatherReading(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall_24h: Optional[float] = None
    source: Optional[str] = None
    observed_at: Optional[str] = None
    available: bool
    message: Optional[str] = None


class ZoneWeatherResponse(BaseModel):
    zone_id: int
    zone_name: str
    weather: WeatherReading


class WeatherRefreshResponse(BaseModel):
    zone_id: int
    zone_name: str
    weather: WeatherReading
    risk_score: float
    risk_level: str
    prediction_source: str
    alert_created: bool
    alert_updated: bool


class WeatherObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_id: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall_24h: Optional[float] = None
    source: Optional[str] = None
    observed_at: Optional[str] = None
    created_at: datetime


class BulkRefreshResult(BaseModel):
    total_zones: int
    updated: int
    weather_unavailable: int
    risk_updated: int
    alerts_generated: int
