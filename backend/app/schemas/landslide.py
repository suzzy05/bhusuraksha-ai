from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class LandslideEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    latitude: float
    longitude: float
    state: Optional[str] = None
    event_date: Optional[datetime] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    source_id: Optional[str] = None
    source_record_id: Optional[str] = None
    data_quality_score: Optional[float] = None
    created_at: datetime


class PaginatedLandslideEvents(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    results: List[LandslideEventOut]


class NearbyLandslideEventOut(LandslideEventOut):
    distance_km: float


class NearbyLandslideEventsResponse(BaseModel):
    query: dict
    spatial_backend: str
    count: int
    results: List[NearbyLandslideEventOut]


class MapLandslideEventsResponse(BaseModel):
    query: dict
    spatial_backend: str
    total_matching: int
    count: int
    truncated: bool
    results: List[LandslideEventOut]
