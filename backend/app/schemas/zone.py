from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ZoneListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    latitude: float
    longitude: float
    risk_score: float
    risk_level: str
    source_type: str
    historical_event_count: Optional[int] = None
    updated_at: datetime


class ZoneEnvironment(BaseModel):
    rainfall_24h: float
    rainfall_7d: float
    humidity: float
    temperature: float
    slope: float
    elevation: float
    vegetation: float
    historical_landslide: bool


class RiskFactors(BaseModel):
    rainfall: float
    slope: float
    vegetation: float
    historical: float
    humidity: float


class ZoneDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    latitude: float
    longitude: float
    risk_score: float
    risk_level: str
    source_type: str
    historical_event_count: Optional[int] = None
    updated_at: datetime
    environment: ZoneEnvironment
    risk_factors: RiskFactors


class RiskPredictionRequest(BaseModel):
    rainfall_24h: float = Field(..., ge=0, description="Rainfall in the last 24 hours (mm)")
    rainfall_7d: float = Field(..., ge=0, description="Rainfall in the last 7 days (mm)")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity (%)")
    temperature: float = Field(..., description="Temperature (Celsius)")
    slope: float = Field(..., ge=0, le=90, description="Terrain slope (degrees)")
    elevation: float = Field(..., ge=0, description="Elevation (meters)")
    vegetation: float = Field(..., ge=0, le=1, description="Vegetation cover fraction (0-1)")
    historical_landslide: bool = Field(..., description="Whether the area has a history of landslides")


class RiskPredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    risk_score: float
    risk_level: str
    prediction_source: str = Field(..., description="'machine_learning' or 'rule_based_fallback'")
    model_available: bool
    risk_factors: Dict[str, float] = Field(..., description="Local, rule-based explanation of this prediction")
    class_probabilities: Optional[Dict[str, float]] = Field(
        None, description="ML class probabilities, present only when prediction_source is machine_learning"
    )
    feature_importance: Optional[Dict[str, float]] = Field(
        None,
        description=(
            "Global RandomForest feature_importances_, NOT specific to this single prediction. "
            "Present only when prediction_source is machine_learning."
        ),
    )
