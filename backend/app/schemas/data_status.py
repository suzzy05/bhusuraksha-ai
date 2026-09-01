from typing import Optional

from pydantic import BaseModel


class DemoDatasetStatus(BaseModel):
    available: bool
    type: str


class SusceptibilityModelStatus(BaseModel):
    available: bool
    coverage: str


class ConfiguredStatus(BaseModel):
    configured: bool


class ProcessedDatasetStatus(BaseModel):
    available: bool


class LiveWeatherStatus(BaseModel):
    provider_configured: bool
    last_refresh: Optional[str] = None
    available: bool


class IndiaMonitoringStatus(BaseModel):
    architecture_ready: bool
    coverage_status: str
    real_data_sources: int
    total_zones: int
    historical_events: int


class RealDataStatus(BaseModel):
    sources_registered: int
    sources_processed: int
    landslide_events: int
    rainfall_observations: int
    dem_available: bool
    landcover_available: bool
    boundaries_available: bool


class DataStatusResponse(BaseModel):
    demo_ml_dataset: DemoDatasetStatus
    susceptibility_model: SusceptibilityModelStatus
    external_landslide_data: ConfiguredStatus
    external_rainfall_data: ConfiguredStatus
    external_dem_data: ConfiguredStatus
    external_vegetation_data: ConfiguredStatus
    processed_dataset: ProcessedDatasetStatus
    live_weather: LiveWeatherStatus
    india_monitoring: IndiaMonitoringStatus
    real_data: RealDataStatus
