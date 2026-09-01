from pydantic import BaseModel


class IndiaSummaryResponse(BaseModel):
    country: str
    monitoring_regions: int
    regions_with_real_data: int
    total_zones: int
    historical_landslide_events: int
    coverage_status: str
