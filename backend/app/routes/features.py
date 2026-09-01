from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.features import FeatureVectorResponse
from app.services.feature_engineering_service import (
    DEFAULT_DENSITY_RADIUS_KM,
    build_feature_vector,
)
from app.services.rainfall_service import DEFAULT_SEARCH_RADIUS_KM

router = APIRouter(tags=["Features"])

MAX_RADIUS_KM = 500


@router.get(
    "/features",
    response_model=FeatureVectorResponse,
    summary="Unified real-data feature vector for a point",
    description=(
        "Combines rainfall accumulation, terrain, land cover, and historical-landslide density — each "
        "field independently available/unavailable depending on what real data actually exists. Never "
        "fabricates a value: an unavailable feature is null, not estimated or defaulted to 0."
    ),
)
def read_feature_vector(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    as_of: Optional[datetime] = Query(None, description="Defaults to now"),
    rainfall_radius_km: float = Query(DEFAULT_SEARCH_RADIUS_KM, gt=0, le=MAX_RADIUS_KM),
    density_radius_km: float = Query(DEFAULT_DENSITY_RADIUS_KM, gt=0, le=MAX_RADIUS_KM),
    db: Session = Depends(get_db),
):
    return build_feature_vector(
        db, lat=lat, lon=lon, as_of=as_of,
        rainfall_radius_km=rainfall_radius_km, density_radius_km=density_radius_km,
    )
