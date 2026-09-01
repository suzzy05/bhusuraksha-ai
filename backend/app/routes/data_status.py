from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.data_status import DataStatusResponse
from app.services import india_monitoring_service, real_data_service, weather_service
from geospatial.config import load_external_data_config
from geospatial.pipeline import PROCESSED_DIR, PROCESSED_RECORDS_FILENAME
from ml.predict import is_model_available
from ml.susceptibility.predict import is_susceptibility_model_available

router = APIRouter(tags=["Data Status"])


@router.get("/data-status", response_model=DataStatusResponse)
def get_data_status(db: Session = Depends(get_db)):
    """Reports which data sources are actually wired up. Never exposes
    filesystem paths — only availability/configuration booleans and counts."""
    config = load_external_data_config()
    processed_path = PROCESSED_DIR / PROCESSED_RECORDS_FILENAME
    india_summary = india_monitoring_service.get_summary(db)

    return DataStatusResponse(
        demo_ml_dataset={"available": is_model_available(), "type": "synthetic_demo"},
        susceptibility_model={
            "available": is_susceptibility_model_available(),
            "coverage": "Uttarakhand + Himachal Pradesh pilot area only, not India-wide",
        },
        external_landslide_data={"configured": config.is_configured("landslide")},
        external_rainfall_data={"configured": config.is_configured("rainfall")},
        external_dem_data={"configured": config.is_configured("dem")},
        external_vegetation_data={"configured": config.is_configured("vegetation")},
        processed_dataset={"available": processed_path.exists()},
        live_weather=weather_service.get_live_weather_status(),
        india_monitoring={
            "architecture_ready": True,
            "coverage_status": india_summary["coverage_status"],
            "real_data_sources": india_summary["registered_data_sources"],
            "total_zones": india_summary["total_zones"],
            "historical_events": india_summary["historical_landslide_events"],
        },
        real_data=real_data_service.get_real_data_status(db),
    )
