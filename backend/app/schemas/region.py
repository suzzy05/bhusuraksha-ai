from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class MonitoringRegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: Optional[str] = None
    district: Optional[str] = None
    region_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geometry_type: Optional[str] = None
    geometry_data: Optional[Any] = None
    is_landslide_prone: Optional[bool] = None
    source_id: Optional[str] = None
    source_type: str
    coverage_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
