from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class RainfallObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    latitude: float
    longitude: float
    station_id: Optional[str] = None
    observed_date: Optional[datetime] = None
    rainfall_mm: Optional[float] = None
    source_id: Optional[str] = None
    source_record_id: Optional[str] = None
    created_at: datetime


class PaginatedRainfallObservations(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    results: List[RainfallObservationOut]


class NearbyRainfallObservationOut(RainfallObservationOut):
    distance_km: float


class NearbyRainfallResponse(BaseModel):
    query: dict
    spatial_backend: str
    count: int
    results: List[NearbyRainfallObservationOut]


class RainfallMapResponse(BaseModel):
    query: dict
    spatial_backend: str
    total_matching: int
    count: int
    truncated: bool
    results: List[RainfallObservationOut]


class RainfallSummaryResponse(BaseModel):
    spatial_backend: str
    search_radius_km: float
    as_of: str
    nearest_station_id: Optional[str] = None
    nearest_station_distance_km: Optional[float] = None
    rainfall_24h: Optional[float] = None
    rainfall_24h_observation_count: int
    rainfall_72h: Optional[float] = None
    rainfall_72h_observation_count: int
    rainfall_7d: Optional[float] = None
    rainfall_7d_observation_count: int
    rainfall_30d: Optional[float] = None
    rainfall_30d_observation_count: int
    antecedent_rainfall_index: Optional[float] = None
    antecedent_observation_count: int
    available: bool
    message: str
