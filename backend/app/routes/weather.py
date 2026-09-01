from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.weather_observation import WeatherObservation
from app.models.zone import Zone
from app.schemas.weather import (
    BulkRefreshResult,
    WeatherObservationOut,
    WeatherRefreshResponse,
    ZoneWeatherResponse,
)
from app.services import weather_service
from app.services.risk_update_service import update_zone_risk

router = APIRouter(prefix="/weather", tags=["Weather"])


def _get_zone_or_404(db: Session, zone_id: int) -> Zone:
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone with id {zone_id} not found")
    return zone


def _store_observation(db: Session, zone_id: int, weather: dict):
    """Only ever stores a row when the provider actually returned data —
    no placeholder/fake observations are recorded."""
    if not weather.get("available"):
        return
    db.add(
        WeatherObservation(
            zone_id=zone_id,
            temperature=weather.get("temperature"),
            humidity=weather.get("humidity"),
            rainfall_24h=weather.get("rainfall_24h"),
            source=weather.get("source"),
            observed_at=weather.get("observed_at"),
        )
    )


def _apply_weather_to_zone(zone: Zone, weather: dict):
    """Only overwrites a field the provider actually returned — a field
    the provider didn't supply keeps the zone's existing stored value."""
    if weather.get("temperature") is not None:
        zone.temperature = weather["temperature"]
    if weather.get("humidity") is not None:
        zone.humidity = weather["humidity"]
    if weather.get("rainfall_24h") is not None:
        zone.rainfall_24h = weather["rainfall_24h"]


@router.get(
    "/{zone_id}",
    response_model=ZoneWeatherResponse,
    summary="Get current live weather for a zone",
    description=(
        "Fetches live weather for the zone's coordinates from the configured provider. "
        "Does not modify stored zone data or recompute risk — see POST /weather/{zone_id}/refresh for that. "
        "Never fabricates a value: any field the provider doesn't return comes back as null, "
        "and `available` is false if the provider could not be reached."
    ),
)
def get_weather(zone_id: int, db: Session = Depends(get_db)):
    zone = _get_zone_or_404(db, zone_id)
    weather = weather_service.get_current_weather(zone.latitude, zone.longitude)
    return ZoneWeatherResponse(zone_id=zone.id, zone_name=zone.name, weather=weather)


@router.post(
    "/{zone_id}/refresh",
    response_model=WeatherRefreshResponse,
    summary="Refresh a zone's live weather and recompute its risk",
    description=(
        "Fetches live weather, updates only the zone fields the provider actually returned "
        "(existing values are preserved for anything unavailable), stores a weather observation "
        "if data was returned, then recomputes risk (ML-first, rule-based fallback — no retraining) "
        "and reconciles alerts without creating duplicates."
    ),
)
def refresh_weather(zone_id: int, db: Session = Depends(get_db)):
    zone = _get_zone_or_404(db, zone_id)
    weather = weather_service.get_current_weather(zone.latitude, zone.longitude)

    _apply_weather_to_zone(zone, weather)
    _store_observation(db, zone.id, weather)

    risk_result = update_zone_risk(db, zone, triggered_by="manual_refresh")
    db.commit()
    db.refresh(zone)

    return WeatherRefreshResponse(
        zone_id=zone.id,
        zone_name=zone.name,
        weather=weather,
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
        prediction_source=risk_result["prediction_source"],
        alert_created=risk_result["alert_created"],
        alert_updated=risk_result["alert_updated"],
    )


@router.post(
    "/refresh-all",
    response_model=BulkRefreshResult,
    summary="Refresh live weather and risk for every monitored zone",
    description=(
        "Runs the same refresh as POST /weather/{zone_id}/refresh for every zone. "
        "Zones are processed independently — one zone's failure (provider timeout, etc.) "
        "does not abort the batch or affect other zones."
    ),
)
def refresh_all_weather(db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    updated = 0
    weather_unavailable = 0
    risk_updated = 0
    alerts_generated = 0

    for zone in zones:
        try:
            weather = weather_service.get_current_weather(zone.latitude, zone.longitude)
            if weather.get("available"):
                _apply_weather_to_zone(zone, weather)
                _store_observation(db, zone.id, weather)
                updated += 1
            else:
                weather_unavailable += 1

            risk_result = update_zone_risk(db, zone, triggered_by="manual_refresh_all")
            risk_updated += 1
            if risk_result.get("alert_created"):
                alerts_generated += 1

            db.commit()
        except Exception:  # noqa: BLE001 - one zone's failure must not abort the batch
            db.rollback()
            continue

    return BulkRefreshResult(
        total_zones=len(zones),
        updated=updated,
        weather_unavailable=weather_unavailable,
        risk_updated=risk_updated,
        alerts_generated=alerts_generated,
    )


@router.get(
    "/{zone_id}/history",
    response_model=List[WeatherObservationOut],
    summary="Recent stored weather observations for a zone",
    description="Returns real, previously-fetched weather observations for a zone, newest first. Empty if none have been recorded yet — never synthesized.",
)
def get_weather_history(zone_id: int, limit: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    _get_zone_or_404(db, zone_id)
    return (
        db.query(WeatherObservation)
        .filter(WeatherObservation.zone_id == zone_id)
        .order_by(WeatherObservation.created_at.desc())
        .limit(limit)
        .all()
    )
