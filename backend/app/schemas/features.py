from typing import Optional

from pydantic import BaseModel


class FeatureVectorResponse(BaseModel):
    feature_schema_version: str
    generated_at: str
    input: dict

    rainfall_24h: Optional[float] = None
    rainfall_72h: Optional[float] = None
    rainfall_7d: Optional[float] = None
    rainfall_30d: Optional[float] = None
    antecedent_rainfall_index: Optional[float] = None
    rainfall_available: bool
    rainfall_spatial_backend: str

    elevation_m: Optional[float] = None
    slope_degrees: Optional[float] = None
    aspect_degrees: Optional[float] = None
    terrain_available: bool

    landcover_category: Optional[str] = None
    landcover_available: bool

    historical_landslide_count: int
    historical_landslide_density_per_km2: float
    historical_density_radius_km: float
    historical_density_spatial_backend: str
