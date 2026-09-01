from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.zone import Zone
from app.seed_data import SEED_ZONES
from app.services.risk_service import calculate_risk

ALERT_SEVERITIES = ("HIGH", "CRITICAL")


def seed_zones(db: Session):
    if db.query(Zone).count() > 0:
        return

    for data in SEED_ZONES:
        result = calculate_risk(
            rainfall_24h=data["rainfall_24h"],
            rainfall_7d=data["rainfall_7d"],
            humidity=data["humidity"],
            temperature=data["temperature"],
            slope=data["slope"],
            elevation=data["elevation"],
            vegetation=data["vegetation"],
            historical_landslide=data["historical_landslide"],
        )

        zone = Zone(
            **data,
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            source_type="demo_seed",
        )
        db.add(zone)

    db.commit()


def _build_alert_content(zone: Zone):
    title = f"LANDSLIDE WARNING - {zone.name}"
    message = (
        f"Location: {zone.name}, {zone.state}\n"
        f"Risk Score: {zone.risk_score}/100\n"
        f"Risk Level: {zone.risk_level}\n"
        "Potential landslide risk detected due to heavy rainfall and steep terrain."
    )
    return title, message


def generate_alerts(db: Session):
    at_risk_zones = db.query(Zone).filter(Zone.risk_level.in_(ALERT_SEVERITIES)).all()

    for zone in at_risk_zones:
        existing_alert = (
            db.query(Alert)
            .filter(Alert.zone_id == zone.id, Alert.is_active.is_(True))
            .first()
        )
        if existing_alert:
            continue

        title, message = _build_alert_content(zone)
        db.add(
            Alert(
                zone_id=zone.id,
                title=title,
                message=message,
                severity=zone.risk_level,
                is_active=True,
            )
        )

    db.commit()
