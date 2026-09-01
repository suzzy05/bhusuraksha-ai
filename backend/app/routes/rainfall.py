from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rainfall_observation import RainfallObservation
from app.schemas.rainfall import (
    NearbyRainfallObservationOut,
    NearbyRainfallResponse,
    PaginatedRainfallObservations,
    RainfallMapResponse,
    RainfallObservationOut,
    RainfallSummaryResponse,
)
from app.services.rainfall_service import DEFAULT_SEARCH_RADIUS_KM, get_rainfall_summary
from app.services.spatial_service import bbox_rainfall, nearby_rainfall

router = APIRouter(tags=["Rainfall"])

MAX_PAGE_SIZE = 200
MAX_RADIUS_KM = 500
MAX_NEARBY_RESULTS = 200
MAX_MAP_RESULTS = 2000
DEFAULT_MAP_LIMIT = 500
MAX_HISTORY_RESULTS = 1000


@router.get(
    "/rainfall",
    response_model=PaginatedRainfallObservations,
    summary="Paginated historical rainfall observations",
    description=(
        "Returns real, registered rainfall observations — empty until an actual dataset has been "
        "ingested (never auto-populated or fabricated). Always paginated."
    ),
)
def list_rainfall(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    station_id: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None, description="Filter by registered data source id"),
    start_date: Optional[datetime] = Query(None, description="Only observations on/after this date"),
    end_date: Optional[datetime] = Query(None, description="Only observations on/before this date"),
    db: Session = Depends(get_db),
):
    query = db.query(RainfallObservation)
    if station_id:
        query = query.filter(RainfallObservation.station_id == station_id)
    if source_id:
        query = query.filter(RainfallObservation.source_id == source_id)
    if start_date:
        query = query.filter(RainfallObservation.observed_date >= start_date)
    if end_date:
        query = query.filter(RainfallObservation.observed_date <= end_date)

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    results = (
        query.order_by(RainfallObservation.observed_date.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedRainfallObservations(page=page, page_size=page_size, total=total, total_pages=total_pages, results=results)


@router.get(
    "/rainfall/summary",
    response_model=RainfallSummaryResponse,
    summary="Real rainfall accumulation windows for a point",
    description=(
        "24h/72h/7d/30d accumulation and an antecedent-rainfall index, computed ONLY from the nearest "
        "real station within radius_km. A window with zero real observations is null, never 0."
    ),
)
def get_summary(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(DEFAULT_SEARCH_RADIUS_KM, gt=0, le=MAX_RADIUS_KM),
    as_of: Optional[datetime] = Query(None, description="Defaults to now"),
    db: Session = Depends(get_db),
):
    return get_rainfall_summary(db, lat=lat, lon=lon, as_of=as_of, radius_km=radius_km)


@router.get(
    "/rainfall/nearby",
    response_model=NearbyRainfallResponse,
    summary="Rainfall observations within a radius of a point",
    description="Spatial radius search — see /landslides/nearby for the identical PostGIS/SQLite-fallback contract.",
)
def get_nearby_rainfall(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=MAX_RADIUS_KM),
    source_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=MAX_NEARBY_RESULTS),
    db: Session = Depends(get_db),
):
    pairs, backend = nearby_rainfall(
        db, lat=lat, lon=lon, radius_km=radius_km, source_id=source_id,
        start_date=start_date, end_date=end_date, limit=limit,
    )
    results = [
        NearbyRainfallObservationOut(
            **RainfallObservationOut.model_validate(obs).model_dump(), distance_km=round(distance, 3)
        )
        for obs, distance in pairs
    ]
    return NearbyRainfallResponse(
        query={"lat": lat, "lon": lon, "radius_km": radius_km, "source_id": source_id},
        spatial_backend=backend,
        count=len(results),
        results=results,
    )


@router.get(
    "/rainfall/map",
    response_model=RainfallMapResponse,
    summary="Rainfall observations within a map viewport bounding box",
    description=f"Bounded viewport query — never the whole inventory. Capped to {MAX_MAP_RESULTS} results.",
)
def get_rainfall_in_bbox(
    min_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    source_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(DEFAULT_MAP_LIMIT, ge=1, le=MAX_MAP_RESULTS),
    db: Session = Depends(get_db),
):
    if min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="min_lat must be less than max_lat")
    if min_lon >= max_lon:
        raise HTTPException(status_code=422, detail="min_lon must be less than max_lon")

    results, total_matching, backend = bbox_rainfall(
        db, min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon,
        source_id=source_id, start_date=start_date, end_date=end_date, limit=limit,
    )
    return RainfallMapResponse(
        query={"min_lat": min_lat, "min_lon": min_lon, "max_lat": max_lat, "max_lon": max_lon},
        spatial_backend=backend,
        total_matching=total_matching,
        count=len(results),
        truncated=total_matching > len(results),
        results=results,
    )


@router.get(
    "/rainfall/history",
    response_model=List[RainfallObservationOut],
    summary="Time series of observations for one station (or point)",
    description=(
        "Pass station_id for a specific station's real readings, ordered oldest-first for charting, or "
        "lat/lon (+ optional radius_km) to use the nearest station within range instead."
    ),
)
def get_rainfall_history(
    station_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(DEFAULT_SEARCH_RADIUS_KM, gt=0, le=MAX_RADIUS_KM),
    source_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(200, ge=1, le=MAX_HISTORY_RESULTS),
    db: Session = Depends(get_db),
):
    if not station_id and (lat is None or lon is None):
        raise HTTPException(status_code=422, detail="Provide either station_id, or both lat and lon")

    if station_id:
        query = db.query(RainfallObservation).filter(RainfallObservation.station_id == station_id)
        if source_id:
            query = query.filter(RainfallObservation.source_id == source_id)
        if start_date:
            query = query.filter(RainfallObservation.observed_date >= start_date)
        if end_date:
            query = query.filter(RainfallObservation.observed_date <= end_date)
        return query.order_by(RainfallObservation.observed_date.asc().nullslast()).limit(limit).all()

    pairs, _backend = nearby_rainfall(
        db, lat=lat, lon=lon, radius_km=radius_km, source_id=source_id,
        start_date=start_date, end_date=end_date, limit=limit,
    )
    if not pairs:
        return []
    nearest_station_id = pairs[0][0].station_id
    if nearest_station_id is None:
        # No station identifier at all in the source data — fall back to
        # the single nearest observation's own coordinates as its identity.
        nearest_lat, nearest_lon = pairs[0][0].latitude, pairs[0][0].longitude
        same_point = [obs for obs, _d in pairs if obs.latitude == nearest_lat and obs.longitude == nearest_lon]
    else:
        same_point = [obs for obs, _d in pairs if obs.station_id == nearest_station_id]
    return sorted(same_point, key=lambda obs: obs.observed_date or datetime.min)[:limit]


@router.get("/rainfall/{observation_id}", response_model=RainfallObservationOut)
def get_rainfall_observation(observation_id: int, db: Session = Depends(get_db)):
    observation = db.query(RainfallObservation).filter(RainfallObservation.id == observation_id).first()
    if not observation:
        raise HTTPException(status_code=404, detail=f"Rainfall observation with id {observation_id} not found")
    return observation
