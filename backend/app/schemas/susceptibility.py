from typing import Optional

from pydantic import BaseModel


class SusceptibilityResponse(BaseModel):
    prediction_source: str
    model_available: bool
    susceptibility_score: Optional[float] = None
    probability: Optional[float] = None
    message: Optional[str] = None
    feature_vector: dict
