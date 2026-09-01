"""Recomputes a zone's risk from its current environmental fields (ML-first,
rule-based fallback — same policy as POST /predict-risk) and reconciles its
alerts. Never retrains the ML model; only re-runs inference. Every
recomputation is logged (Phase 16) with its inputs, data availability, and
which prediction path produced it — an auditable history, not just a
side-effecting update.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.risk_update_log import RiskUpdateLog
from app.models.zone import Zone
from app.services.risk_service import calculate_risk
from ml.predict import predict_risk_ml

ALERT_SEVERITIES = ("HIGH", "CRITICAL")


def _zone_features(zone: Zone) -> dict:
    return {
        "rainfall_24h": zone.rainfall_24h,
        "rainfall_7d": zone.rainfall_7d,
        "humidity": zone.humidity,
        "temperature": zone.temperature,
        "slope": zone.slope,
        "elevation": zone.elevation,
        "vegetation": zone.vegetation,
        "historical_landslide": zone.historical_landslide,
    }


def _data_availability(features: dict) -> dict:
    return {key: value is not None for key, value in features.items()}


def compute_zone_risk(zone: Zone) -> dict:
    features = _zone_features(zone)

    # Always compute the rule-based factor breakdown — it's the local,
    # per-zone explanation regardless of which path actually produced the
    # risk score (same policy as POST /predict-risk).
    rule_result = calculate_risk(**features)

    ml_result = None
    try:
        ml_result = predict_risk_ml(features)
    except Exception:  # noqa: BLE001 - ML must never break a risk update
        ml_result = None

    if ml_result is not None:
        return {
            "risk_score": ml_result["risk_score"],
            "risk_level": ml_result["predicted_risk_level"],
            "prediction_source": "machine_learning",
            "factors": rule_result["factors"],
        }

    return {
        "risk_score": rule_result["risk_score"],
        "risk_level": rule_result["risk_level"],
        "prediction_source": "rule_based_fallback",
        "factors": rule_result["factors"],
    }


def _top_factor_reason(factors: dict) -> str:
    if not factors:
        return "Risk factors unavailable."
    top_factor = max(factors, key=factors.get)
    label = top_factor.replace("_", " ").title()
    return f"Primary contributing factor: {label}."


def _build_alert_content(zone: Zone, reason: str):
    title = f"LANDSLIDE WARNING - {zone.name}"
    message = (
        f"Location: {zone.name}, {zone.state}\n"
        f"Risk Score: {zone.risk_score}/100\n"
        f"Risk Level: {zone.risk_level}\n"
        f"{reason}"
    )
    return title, message


def reconcile_alerts(db: Session, zone: Zone, factors: dict) -> dict:
    """Keeps at most one ACTIVE (or ACKNOWLEDGED) alert per zone, matching
    its current severity. Never deletes a row — a superseded or no-longer-
    warranted alert transitions to status="resolved" (with resolved_at
    set) and is kept as history, never deleted."""
    now = datetime.utcnow()
    open_alerts = db.query(Alert).filter(Alert.zone_id == zone.id, Alert.is_active.is_(True)).all()

    if zone.risk_level not in ALERT_SEVERITIES:
        deactivated = False
        for alert in open_alerts:
            alert.is_active = False
            alert.status = "resolved"
            alert.resolved_at = now
            deactivated = True
        return {"alert_created": False, "alert_updated": deactivated}

    if any(alert.severity == zone.risk_level for alert in open_alerts):
        return {"alert_created": False, "alert_updated": False}

    severity_changed = bool(open_alerts)
    for alert in open_alerts:
        alert.is_active = False
        alert.status = "resolved"
        alert.resolved_at = now

    reason = _top_factor_reason(factors)
    title, message = _build_alert_content(zone, reason)
    db.add(
        Alert(
            zone_id=zone.id,
            title=title,
            message=message,
            severity=zone.risk_level,
            is_active=True,
            status="active",
            risk_score=zone.risk_score,
            reason=reason,
        )
    )
    return {"alert_created": True, "alert_updated": severity_changed}


def update_zone_risk(db: Session, zone: Zone, triggered_by: str = "manual_refresh") -> dict:
    """Recomputes risk_score/risk_level/updated_at for `zone`, reconciles
    its alerts, and records an auditable RiskUpdateLog row. Does not
    commit — the caller controls the transaction boundary.

    A "derived" zone (Phase 21 — built from real historical event
    clusters, not a real environmental sensor) starts with no real
    rainfall/slope/etc. — feeding its placeholder environment columns into
    the rule-based or ML engine would fabricate a plausible-looking risk
    score. This is a no-op for those zones UNTIL `terrain_data_real` is set
    (Phase 23 — real slope/elevation actually read from a real DEM for this
    zone's real coordinates): risk_score/risk_level/alerts are left exactly
    as they are (UNKNOWN/0.0, no alert), and the log records why. Once
    `terrain_data_real` is True, the zone has real terrain + real live
    weather (Phase 6) + real historical_landslide — enough real inputs
    that normal computation below is no longer fabricating from
    placeholders (only `vegetation` stays a documented neutral default,
    same as every zone including the original demo ones)."""
    if zone.source_type == "derived" and not zone.terrain_data_real:
        db.add(
            RiskUpdateLog(
                zone_id=zone.id,
                triggered_by=triggered_by,
                inputs=_zone_features(zone),
                data_availability={"real_environmental_data": False},
                prediction_source="unavailable_derived_zone_no_real_environment",
                risk_score=zone.risk_score,
                risk_level=zone.risk_level,
            )
        )
        return {
            "risk_score": zone.risk_score,
            "risk_level": zone.risk_level,
            "prediction_source": "unavailable_derived_zone_no_real_environment",
            "alert_created": False,
            "alert_updated": False,
        }

    features = _zone_features(zone)
    result = compute_zone_risk(zone)
    zone.risk_score = result["risk_score"]
    zone.risk_level = result["risk_level"]
    zone.updated_at = datetime.utcnow()

    alert_result = reconcile_alerts(db, zone, result["factors"])

    db.add(
        RiskUpdateLog(
            zone_id=zone.id,
            triggered_by=triggered_by,
            inputs=features,
            data_availability=_data_availability(features),
            prediction_source=result["prediction_source"],
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
        )
    )

    return {
        "risk_score": zone.risk_score,
        "risk_level": zone.risk_level,
        "prediction_source": result["prediction_source"],
        **alert_result,
    }
