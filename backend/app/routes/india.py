from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.india import IndiaSummaryResponse
from app.services.india_monitoring_service import get_summary

router = APIRouter(prefix="/india", tags=["India Monitoring"])


@router.get(
    "/summary",
    response_model=IndiaSummaryResponse,
    summary="Pan-India monitoring coverage summary",
    description=(
        "Reports actual monitoring coverage counts — never claims national coverage. "
        "coverage_status is a conservative, count-based classification: 'prototype' until real "
        "regional data and historical events actually exist in the database."
    ),
)
def get_india_summary(db: Session = Depends(get_db)):
    summary = get_summary(db)
    return IndiaSummaryResponse(
        country="India",
        monitoring_regions=summary["monitoring_regions"],
        regions_with_real_data=summary["regions_with_real_data"],
        total_zones=summary["total_zones"],
        historical_landslide_events=summary["historical_landslide_events"],
        coverage_status=summary["coverage_status"],
    )
