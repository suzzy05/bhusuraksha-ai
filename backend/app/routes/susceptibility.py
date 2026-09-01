from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.susceptibility import SusceptibilityResponse
from app.services.feature_engineering_service import DEFAULT_DENSITY_RADIUS_KM, build_feature_vector
from app.services.rainfall_service import DEFAULT_SEARCH_RADIUS_KM
from ml.susceptibility.predict import is_susceptibility_model_available, predict_susceptibility

router = APIRouter(tags=["Susceptibility"])

MAX_RADIUS_KM = 500
PREDICTION_SOURCE = "susceptibility_ml"


@router.get(
    "/susceptibility",
    response_model=SusceptibilityResponse,
    summary="Real-data landslide susceptibility score for a point (Phase 20)",
    description=(
        "A susceptibility SCORE — relative spatial propensity learned from real presence/pseudo-absence "
        "data — never a validated forecast of a future event. Always discloses prediction_source="
        "'susceptibility_ml' and model_available, and returns model_available=false with the underlying "
        "real feature vector (never a guessed score) if no model is trained yet or a critical feature is "
        "missing for this coordinate. See docs/ML_LIMITATIONS.md."
    ),
)
def read_susceptibility(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    as_of: Optional[datetime] = Query(None, description="Defaults to now"),
    rainfall_radius_km: float = Query(DEFAULT_SEARCH_RADIUS_KM, gt=0, le=MAX_RADIUS_KM),
    density_radius_km: float = Query(DEFAULT_DENSITY_RADIUS_KM, gt=0, le=MAX_RADIUS_KM),
    db: Session = Depends(get_db),
):
    features = build_feature_vector(
        db, lat=lat, lon=lon, as_of=as_of,
        rainfall_radius_km=rainfall_radius_km, density_radius_km=density_radius_km,
    )

    if not is_susceptibility_model_available():
        return SusceptibilityResponse(
            prediction_source=PREDICTION_SOURCE,
            model_available=False,
            message="No susceptibility model is trained yet. See docs/ML_LIMITATIONS.md.",
            feature_vector=features,
        )

    result = predict_susceptibility(features)
    if result is None:
        return SusceptibilityResponse(
            prediction_source=PREDICTION_SOURCE,
            model_available=True,
            message="A susceptibility model is trained, but a critical real feature (rainfall/terrain/land cover) is unavailable at this coordinate.",
            feature_vector=features,
        )

    return SusceptibilityResponse(
        prediction_source=PREDICTION_SOURCE,
        model_available=True,
        susceptibility_score=result["susceptibility_score"],
        probability=result["probability"],
        feature_vector=features,
    )
