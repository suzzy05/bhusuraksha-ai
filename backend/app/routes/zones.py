from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.risk_update_log import RiskUpdateLog
from app.models.zone import Zone
from app.schemas.risk_update_log import RiskUpdateLogOut
from app.schemas.zone import RiskFactors, ZoneDetail, ZoneEnvironment, ZoneListItem
from app.services.risk_service import calculate_risk

router = APIRouter(tags=["Zones"])

MAX_RISK_UPDATE_HISTORY = 200


@router.get("/zones", response_model=List[ZoneListItem])
def get_zones(db: Session = Depends(get_db)):
    return db.query(Zone).order_by(Zone.id).all()


@router.get("/zones/{zone_id}", response_model=ZoneDetail)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone with id {zone_id} not found")

    # A "derived" zone without real terrain (Phase 21/23 — built from real
    # historical event clusters, not a real environmental sensor) has no
    # real rainfall/slope/etc. to feed the rule-based engine — its
    # environment columns are placeholder defaults, never a real
    # measurement. Running calculate_risk on placeholders would produce a
    # plausible-looking but entirely fabricated risk_factors breakdown, so
    # this is skipped entirely: risk_factors is honestly all-zero, matching
    # the zone's own risk_score=0.0/risk_level="UNKNOWN". Once
    # terrain_data_real is True the zone has real slope/elevation + real
    # live weather, so normal computation below is legitimate.
    if zone.source_type == "derived" and not zone.terrain_data_real:
        factors = {"rainfall": 0.0, "slope": 0.0, "vegetation": 0.0, "historical": 0.0, "humidity": 0.0}
    else:
        result = calculate_risk(
            rainfall_24h=zone.rainfall_24h,
            rainfall_7d=zone.rainfall_7d,
            humidity=zone.humidity,
            temperature=zone.temperature,
            slope=zone.slope,
            elevation=zone.elevation,
            vegetation=zone.vegetation,
            historical_landslide=zone.historical_landslide,
        )
        factors = result["factors"]

    return ZoneDetail(
        id=zone.id,
        name=zone.name,
        state=zone.state,
        latitude=zone.latitude,
        longitude=zone.longitude,
        risk_score=zone.risk_score,
        risk_level=zone.risk_level,
        source_type=zone.source_type,
        historical_event_count=zone.historical_event_count,
        updated_at=zone.updated_at,
        environment=ZoneEnvironment(
            rainfall_24h=zone.rainfall_24h,
            rainfall_7d=zone.rainfall_7d,
            humidity=zone.humidity,
            temperature=zone.temperature,
            slope=zone.slope,
            elevation=zone.elevation,
            vegetation=zone.vegetation,
            historical_landslide=zone.historical_landslide,
        ),
        risk_factors=RiskFactors(**factors),
    )


@router.get(
    "/zones/{zone_id}/risk-updates",
    response_model=List[RiskUpdateLogOut],
    summary="Auditable risk-recomputation history for a zone",
    description=(
        "Every risk recomputation (manual refresh, refresh-all, or the scheduled worker) is logged here "
        "with its real inputs, which fields were actually available, and the prediction source used."
    ),
)
def get_zone_risk_updates(
    zone_id: int,
    limit: int = Query(50, ge=1, le=MAX_RISK_UPDATE_HISTORY),
    db: Session = Depends(get_db),
):
    if not db.query(Zone).filter(Zone.id == zone_id).first():
        raise HTTPException(status_code=404, detail=f"Zone with id {zone_id} not found")

    return (
        db.query(RiskUpdateLog)
        .filter(RiskUpdateLog.zone_id == zone_id)
        .order_by(RiskUpdateLog.created_at.desc())
        .limit(limit)
        .all()
    )
