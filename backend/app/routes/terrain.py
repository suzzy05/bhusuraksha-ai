from fastapi import APIRouter, Query

from app.schemas.terrain import TerrainFeaturesResponse
from app.services.terrain_service import get_terrain_features

router = APIRouter(tags=["Terrain"])


@router.get(
    "/terrain/features",
    response_model=TerrainFeaturesResponse,
    summary="Real DEM-derived elevation/slope/aspect for a point",
    description=(
        "Only returns real values when a DEM is configured (BHUSURAKSHA_DEM_DATA_PATH) and the optional "
        "'rasterio' package is installed — otherwise available=false with a clear reason. Never estimates "
        "a value. Slope/aspect additionally require a full 3x3 neighborhood, so a coordinate at the DEM's "
        "edge may report elevation with slope/aspect still null."
    ),
)
def read_terrain_features(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    return get_terrain_features(lat=lat, lon=lon)
