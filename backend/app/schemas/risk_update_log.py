from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiskUpdateLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone_id: int
    triggered_by: str
    inputs: dict
    data_availability: dict
    prediction_source: str
    risk_score: float
    risk_level: str
    created_at: datetime
