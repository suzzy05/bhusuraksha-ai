from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.landslide_event import LandslideEvent
from app.schemas.landslide import (
    LandslideEventOut,
    MapLandslideEventsResponse,
    NearbyLandslideEventOut,
    NearbyLandslideEventsResponse,
    PaginatedLandslideEvents,
)
from app.services.spatial_service import bbox_events, nearby_events

router = APIRouter(tags=["Landslide Events"])

MAX_PAGE_SIZE = 200
MAX_RADIUS_KM = 500
MAX_NEARBY_RESULTS = 200
MAX_MAP_RESULTS = 2000
DEFAULT_MAP_LIMIT = 500


@router.get(
    "/landslides",
    response_model=PaginatedLandslideEvents,
    summary="Paginated historical landslide events",
    description=(
        "Returns real, registered historical landslide event records — this table is empty until an "
        "actual dataset has been ingested (never auto-populated or fabricated). Always paginated; "
        "page_size is capped to keep responses bounded."
    ),
)
def list_landslides(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    state: Optional[str] = Query(None, description="Filter by state, only if the source dataset supplied one"),
    source_id: Optional[str] = Query(None, description="Filter by registered data source id"),
    start_date: Optional[datetime] = Query(None, description="Only events on/after this date"),
    end_date: Optional[datetime] = Query(None, description="Only events on/before this date"),
    db: Session = Depends(get_db),
):
    query = db.query(LandslideEvent)
    if state:
        query = query.filter(LandslideEvent.state == state)
    if source_id:
        query = query.filter(LandslideEvent.source_id == source_id)
    if start_date:
        query = query.filter(LandslideEvent.event_date >= start_date)
    if end_date:
        query = query.filter(LandslideEvent.event_date <= end_date)

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    results = (
        query.order_by(LandslideEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )

    return PaginatedLandslideEvents(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        results=results,
    )


@router.get(
    "/landslides/nearby",
    response_model=NearbyLandslideEventsResponse,
    summary="Historical landslide events within a radius of a point",
    description=(
        "Spatial radius search. On PostgreSQL, uses PostGIS ST_DWithin/ST_Distance (geography, meters-accurate). "
        "On SQLite (local dev), falls back to a bounding-box pre-filter plus an exact Python haversine distance — "
        "response.spatial_backend tells you which; SQLite is never presented as PostGIS-equivalent."
    ),
)
def get_nearby_landslides(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the search center"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the search center"),
    radius_km: float = Query(..., gt=0, le=MAX_RADIUS_KM, description=f"Search radius in km, max {MAX_RADIUS_KM}"),
    source_id: Optional[str] = Query(None, description="Filter by registered data source id"),
    start_date: Optional[datetime] = Query(None, description="Only events on/after this date"),
    end_date: Optional[datetime] = Query(None, description="Only events on/before this date"),
    limit: int = Query(50, ge=1, le=MAX_NEARBY_RESULTS),
    db: Session = Depends(get_db),
):
    pairs, backend = nearby_events(
        db, lat=lat, lon=lon, radius_km=radius_km, source_id=source_id,
        start_date=start_date, end_date=end_date, limit=limit,
    )
    results = [
        NearbyLandslideEventOut(**LandslideEventOut.model_validate(event).model_dump(), distance_km=round(distance, 3))
        for event, distance in pairs
    ]
    return NearbyLandslideEventsResponse(
        query={"lat": lat, "lon": lon, "radius_km": radius_km, "source_id": source_id},
        spatial_backend=backend,
        count=len(results),
        results=results,
    )


@router.get(
    "/landslides/map",
    response_model=MapLandslideEventsResponse,
    summary="Historical landslide events within a map viewport bounding box",
    description=(
        "Bounded viewport query for map rendering — never returns the whole inventory. Capped to "
        f"{MAX_MAP_RESULTS} results; `truncated` is true when more events actually match than were returned."
    ),
)
def get_landslides_in_bbox(
    min_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    source_id: Optional[str] = Query(None, description="Filter by registered data source id"),
    start_date: Optional[datetime] = Query(None, description="Only events on/after this date"),
    end_date: Optional[datetime] = Query(None, description="Only events on/before this date"),
    limit: int = Query(DEFAULT_MAP_LIMIT, ge=1, le=MAX_MAP_RESULTS),
    db: Session = Depends(get_db),
):
    if min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="min_lat must be less than max_lat")
    if min_lon >= max_lon:
        raise HTTPException(status_code=422, detail="min_lon must be less than max_lon")

    results, total_matching, backend = bbox_events(
        db, min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon,
        source_id=source_id, start_date=start_date, end_date=end_date, limit=limit,
    )
    return MapLandslideEventsResponse(
        query={"min_lat": min_lat, "min_lon": min_lon, "max_lat": max_lat, "max_lon": max_lon},
        spatial_backend=backend,
        total_matching=total_matching,
        count=len(results),
        truncated=total_matching > len(results),
        results=results,
    )


@router.get("/landslides/{event_id}", response_model=LandslideEventOut)
def get_landslide(event_id: int, db: Session = Depends(get_db)):
    event = db.query(LandslideEvent).filter(LandslideEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Landslide event with id {event_id} not found")
    return event
