from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.monitoring_region import MonitoringRegion
from app.schemas.region import MonitoringRegionOut

router = APIRouter(tags=["Monitoring Regions"])

# MonitoringRegion is deliberately not bulk-populated (see Phase 7 —
# no synthetic India-wide grid), so a simple capped list is enough for now.
MAX_REGIONS_RETURNED = 500


@router.get(
    "/regions",
    response_model=List[MonitoringRegionOut],
    summary="List monitoring regions",
    description="Lists registered monitoring regions. Empty until real regions are actually registered — never auto-populated with a synthetic grid.",
)
def list_regions(
    state: Optional[str] = Query(None, description="Filter by state"),
    source_type: Optional[str] = Query(
        None, description="Filter by data provenance: demo_seed, external_real, or derived"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(MonitoringRegion)
    if state:
        query = query.filter(MonitoringRegion.state == state)
    if source_type:
        query = query.filter(MonitoringRegion.source_type == source_type)
    return query.order_by(MonitoringRegion.id).limit(MAX_REGIONS_RETURNED).all()


@router.get("/regions/{region_id}", response_model=MonitoringRegionOut)
def get_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(MonitoringRegion).filter(MonitoringRegion.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail=f"Monitoring region with id {region_id} not found")
    return region
