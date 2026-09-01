from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertOut

router = APIRouter(tags=["Alerts"])


@router.get("/alerts", response_model=List[AlertOut])
def get_alerts(
    status: str = Query(
        "active",
        pattern="^(active|acknowledged|resolved|all)$",
        description=(
            "active (default, matches prior behavior — includes acknowledged-but-not-resolved alerts) | "
            "acknowledged (only alerts a human has acknowledged) | resolved | all"
        ),
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)
    if status == "active":
        query = query.filter(Alert.is_active.is_(True))
    elif status == "acknowledged":
        query = query.filter(Alert.status == "acknowledged")
    elif status == "resolved":
        query = query.filter(Alert.is_active.is_(False))
    return query.order_by(Alert.created_at.desc()).all()


def _get_alert_or_404(db: Session, alert_id: int) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert with id {alert_id} not found")
    return alert


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertOut,
    summary="Mark an alert acknowledged",
    description="A human has seen this alert. It stays is_active=True — acknowledging is not resolving.",
)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = _get_alert_or_404(db, alert_id)
    if alert.status == "resolved":
        raise HTTPException(status_code=409, detail="Cannot acknowledge an already-resolved alert")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=AlertOut,
    summary="Mark an alert resolved",
    description="Never deletes the alert — it moves to History, kept as a permanent audit record.",
)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = _get_alert_or_404(db, alert_id)
    alert.status = "resolved"
    alert.is_active = False
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert
