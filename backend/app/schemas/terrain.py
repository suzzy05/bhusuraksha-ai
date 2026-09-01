from typing import Optional

from pydantic import BaseModel


class TerrainFeaturesResponse(BaseModel):
    available: bool
    elevation_m: Optional[float] = None
    slope_degrees: Optional[float] = None
    aspect_degrees: Optional[float] = None
    message: str
