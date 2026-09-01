from fastapi import APIRouter, Query

from app.schemas.landcover import LandcoverResponse
from app.services.landcover_service import get_landcover

router = APIRouter(tags=["Land Cover"])


@router.get(
    "/landcover",
    response_model=LandcoverResponse,
    summary="Real land-cover classification for a point",
    description=(
        "Only returns a real classification when a land-cover raster is configured "
        "(BHUSURAKSHA_LANDCOVER_PATH) and 'rasterio' is installed — otherwise available=false. "
        "normalized_category is 'unknown' unless BHUSURAKSHA_LANDCOVER_SCHEME names a recognized, "
        "real published legend (see geospatial/landcover_schemes.py) — never guessed."
    ),
)
def read_landcover(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    return get_landcover(lat=lat, lon=lon)
