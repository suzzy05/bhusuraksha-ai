from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base

ALERT_STATUSES = ("active", "acknowledged", "resolved")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # `is_active` is kept (and kept in sync with `status`) for backward
    # compatibility with the existing GET /alerts?status=active|resolved
    # contract and frontend Alert Center — never remove it out from under
    # existing callers. `status` is the real Phase 16 lifecycle: a
    # resolved alert always has is_active=False, but an "active" and an
    # "acknowledged" alert are both is_active=True (acknowledged just
    # means a human has seen it — it isn't resolved).
    is_active = Column(Boolean, default=True)
    status = Column(String, nullable=False, default="active")

    # Real values captured at alert-creation time — not re-derived from
    # the zone later (a zone's risk score can keep changing after the
    # alert exists; the alert should describe the moment it fired).
    risk_score = Column(Float, nullable=True)
    reason = Column(String, nullable=True)

    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
